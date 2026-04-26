import sys
import time

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver, tentar_encontrar_elemento

logger = setup_logging('jetmar')


def extrair_dados_card(card, index: int, page_url: str) -> dict:
    try:
        destino_selectors = [
            'a.g-package-name',
            'h5.mb-lg-1',
            'h5',
            '.col.g-package-name',
            'h1', 'h2', 'h3', 'h4', 'h6'
        ]
        destino = tentar_encontrar_elemento(card, destino_selectors, "Destino não encontrado")

        descricao_selectors = [
            'div.g-package-value-adds.g-truncate-long.secondary-text',
            'div.g-package-value-adds.g-truncate-long',
            'div.g-package-value-adds',
            'div[class*="value"]',
            'div.g-truncate-long'
        ]
        descricao = tentar_encontrar_elemento(card, descricao_selectors, "Descrição não encontrada")

        preco_completo = ""

        try:
            moeda_element = card.find_element(By.CSS_SELECTOR, 'span.g-flight-price-currency')
            valor_element = card.find_element(By.CSS_SELECTOR, 'span.g-flight-price')
            moeda = moeda_element.text.strip()
            valor = valor_element.text.strip()
            if moeda and valor:
                preco_completo = f"{moeda} {valor}"
                logger.debug(f"Card {index}: Preço extraído (método 1) - {preco_completo}")
        except Exception as e:
            logger.debug(f"Card {index}: Método 1 falhou: {e}")

        if not preco_completo:
            try:
                price_containers = card.find_elements(By.CSS_SELECTOR, 'app-package-price, div.col-auto.pr-0')
                for container in price_containers:
                    try:
                        moeda = container.find_element(By.CSS_SELECTOR, 'span.g-flight-price-currency').text.strip()
                        valor = container.find_element(By.CSS_SELECTOR, 'span.g-flight-price').text.strip()
                        if moeda and valor:
                            preco_completo = f"{moeda} {valor}"
                            logger.debug(f"Card {index}: Preço extraído (método 2) - {preco_completo}")
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Card {index}: Método 2 falhou: {e}")

        if not preco_completo:
            try:
                price_divs = card.find_elements(By.CSS_SELECTOR, 'div.d-flex.align-items-center')
                for div in price_divs:
                    spans = div.find_elements(By.TAG_NAME, 'span')
                    if len(spans) >= 2:
                        textos = [s.text.strip() for s in spans if s.text.strip()]
                        if len(textos) >= 2:
                            if textos[0] in ['USD', 'BRL', 'EUR', 'ARS'] or textos[0].startswith('$'):
                                preco_completo = f"{textos[0]} {textos[1]}"
                                logger.debug(f"Card {index}: Preço via d-flex - {preco_completo}")
                                break
            except Exception as e:
                logger.debug(f"Card {index}: Método 3 falhou: {e}")

        if not preco_completo:
            try:
                texto_completo = card.text
                import re
                patterns = [
                    r'(USD|BRL|EUR|ARS)\s*(\d[\d.,]*)',
                    r'(\$|R\$|€)\s*(\d[\d.,]*)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, texto_completo, re.IGNORECASE)
                    if match:
                        if len(match.groups()) == 2:
                            preco_completo = f"{match.group(1)} {match.group(2)}"
                        else:
                            preco_completo = match.group(0)
                        logger.debug(f"Card {index}: Preço via regex - {preco_completo}")
                        break
            except Exception as e:
                logger.debug(f"Card {index}: Método regex falhou: {e}")

        if not preco_completo:
            preco_completo = "Preço não encontrado"
            logger.warning(f"Card {index}: NENHUM MÉTODO conseguiu extrair o preço")
            try:
                html_snippet = card.get_attribute('outerHTML')[:500]
                logger.warning(f"Card {index}: HTML snippet: {html_snippet}")
            except:
                pass

        logger.debug(f"Card {index}: {destino} - {preco_completo}")

        return {
            "data_extracao": config.DATA_EXTRACAO,
            "destino": destino,
            "descricao": descricao,
            "preco_completo": preco_completo,
            "url": page_url
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index}: {e}")
        return None


def main():
    logger.info("Iniciando Jetmar")

    TABLE_NAME = "Jetmar"
    TABLE_SCHEMA = """
        data_extracao DATE,
        destino VARCHAR,
        descricao VARCHAR,
        preco_completo VARCHAR,
        url VARCHAR
    """
    FIELDS = ["destino", "descricao", "preco_completo", "url"]

    logger.info(f"Criando/verificando tabela {TABLE_NAME}...")
    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    logger.info("Tabela criada/verificada com sucesso")

    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()

    try:
        url = "https://www.jetmar.com.uy/paquetes/shop?location=america%20del%20sur,brasil"
        logger.info(f"Acessando: {url}")
        driver.get(url)

        logger.info("Aguardando carregamento da página...")
        WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'app-package-search-result'))
        )

        time.sleep(3)

        logger.info("Carregando todos os pacotes disponíveis...")
        max_attempts = 20
        attempts = 0

        while attempts < max_attempts:
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                button_selectors = [
                    'button.mat-raised-button',
                    'button[class*="more"]',
                    'button[class*="load"]',
                    'span.mat-button-wrapper',
                    '//button[contains(text(), "Ver los siguientes")]',
                    '//button[contains(text(), "siguientes")]',
                    '//span[contains(text(), "Ver los siguientes")]/..'
                ]

                button_found = False
                for selector in button_selectors:
                    try:
                        if selector.startswith('//'):
                            buttons = driver.find_elements(By.XPATH, selector)
                        else:
                            buttons = driver.find_elements(By.CSS_SELECTOR, selector)

                        for button in buttons:
                            button_text = button.text.lower()
                            if 'siguiente' in button_text or 'more' in button_text or 'más' in button_text:
                                logger.info(f"Clicando no botão 'carregar mais' (tentativa {attempts + 1})...")
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                time.sleep(1)
                                button.click()
                                button_found = True
                                attempts += 1
                                time.sleep(3)
                                break

                        if button_found:
                            break
                    except:
                        continue

                if not button_found:
                    logger.info("Botão 'carregar mais' não encontrado - todos os pacotes foram carregados")
                    break

            except Exception as e:
                logger.debug(f"Erro ao tentar carregar mais pacotes: {e}")
                break

        logger.info("Fazendo scroll final para garantir carregamento completo...")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

        logger.info("Aguardando preços carregarem...")
        time.sleep(5)

        seletores_possiveis = [
            'app-package-search-result',
            'div.row.d-flex.justify-content-center app-package-search-result',
            '[class*="package"]',
            'div[class*="result"]'
        ]

        pacotes = []
        for seletor in seletores_possiveis:
            try:
                pacotes = driver.find_elements(By.CSS_SELECTOR, seletor)
                if pacotes:
                    logger.info(f"Encontrados {len(pacotes)} pacotes com seletor: '{seletor}'")
                    break
            except:
                continue

        if not pacotes:
            logger.warning("Nenhum pacote encontrado na página.")
            try:
                screenshot_path = f"/app/data/debug_screenshots/jetmar_no_cards.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Screenshot salvo em: {screenshot_path}")
            except Exception as se:
                logger.error(f"Falha ao salvar screenshot: {se}")
            return

        resultados = []
        for index, pacote in enumerate(pacotes, 1):
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", pacote)
                time.sleep(1.5)
            except:
                pass

            resultado = extrair_dados_card(pacote, index, url)
            if resultado and resultado["destino"] != "Destino não encontrado":
                resultados.append(resultado)

            time.sleep(0.5)

        logger.info(f"Total de pacotes extraídos: {len(resultados)}")

        novos_registros = []
        registros_duplicados = 0

        for r in resultados:
            registro_tuple = (
                r["destino"],
                r["descricao"],
                r["preco_completo"],
                r["url"]
            )

            if registro_tuple not in registros_existentes:
                novos_registros.append((
                    r["data_extracao"],
                    r["destino"],
                    r["descricao"],
                    r["preco_completo"],
                    r["url"]
                ))
            else:
                registros_duplicados += 1

        logger.info(f"Registros duplicados (ignorados): {registros_duplicados}")
        logger.info(f"Novos registros a serem inseridos: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS,
                novos_registros
            )
            logger.info(f"Dados inseridos com sucesso: {len(novos_registros)} novos registros")

            for i, reg in enumerate(novos_registros[:5], 1):
                logger.info(f"Novo registro {i}: {reg[1]} - {reg[3]}")
        else:
            logger.info("Nenhum registro novo encontrado. Todos os pacotes já existem no banco.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total_registros}")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        try:
            screenshot_path = f"/app/data/debug_screenshots/jetmar_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Jetmar finalizado")


if __name__ == "__main__":
    main()
