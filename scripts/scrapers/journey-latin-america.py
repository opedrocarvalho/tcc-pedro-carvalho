import sys
import time

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver, tentar_encontrar_elemento

logger = setup_logging('journey_latin_america')


def scroll_e_carregar_cards(driver, timeout=30):

    end_time = time.time() + timeout
    cards_anteriores = 0

    while time.time() < end_time:
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)

        cards_atuais = len(driver.find_elements(By.CSS_SELECTOR, "div.o-card__content"))

        if cards_atuais == cards_anteriores and cards_atuais > 0:
            logger.debug("Scroll da página finalizado, sem novos cards.")
            break

        cards_anteriores = cards_atuais

    cards = driver.find_elements(By.CSS_SELECTOR, "div.o-card__content")
    logger.debug(f"Cards encontrados nesta página após scroll: {len(cards)}")
    return cards

def verificar_proxima_pagina(driver):

    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        botao_next = driver.find_element(By.CSS_SELECTOR, ".o-pagination__arrow.o-pagination__arrow--next.u-pointer")
        if botao_next.is_displayed() and botao_next.is_enabled():
            return botao_next

        seletores_alternativos = [
            ".o-pagination__arrow--next",
            "[class*='o-pagination__arrow--next']",
            "[class*='pagination__arrow--next']"
        ]

        for seletor in seletores_alternativos:
            try:
                botao_alt = driver.find_element(By.CSS_SELECTOR, seletor)
                if botao_alt.is_displayed() and botao_alt.is_enabled():
                    return botao_alt
            except:
                continue

        return None

    except:
        logger.info("Nenhum botão 'próxima página' encontrado.")
        return None

def extrair_dados_card(card, index_str: str, driver) -> dict:

    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
        time.sleep(0.5)

        titulo = "Título não encontrado"
        url_detalhes = ""
        try:
            titulo_element = card.find_element(By.CSS_SELECTOR, "a.o-card__content__title")
            titulo = titulo_element.text.strip()
            url_detalhes = titulo_element.get_attribute("href") or ""
        except:
            try:
                titulo_element = card.find_element(By.CSS_SELECTOR, ".o-card__content__title, h3, h2")
                titulo = titulo_element.text.strip()
                url_detalhes = titulo_element.get_attribute("href") or ""
            except Exception as e:
                logger.debug(f"Card {index_str}: Não foi possível extrair título/URL: {e}")

        try:
            categorias = card.find_elements(By.CSS_SELECTOR, ".o-card__content__tag, .tag, .category")
            categorias_texto = [cat.text.strip() for cat in categorias if cat.text.strip()]
            descricao = " | ".join(categorias_texto) if categorias_texto else tentar_encontrar_elemento(card, [".o-card__content__text", "p", ".description", ".text"], "Descrição não encontrada")
        except:
            descricao = tentar_encontrar_elemento(card, [".o-card__content__text", "p", ".description", ".text"], "Descrição não encontrada")

        try:
            duracao_element = card.find_element(By.CSS_SELECTOR, ".o-text")
            duracao_text = duracao_element.text.strip()
            duracao = duracao_text.split('\n')[0] if '\n' in duracao_text else duracao_text
        except:
            duracao = "Duração não encontrada"

        preco = tentar_encontrar_elemento(card, [".u-color--purple.u-weight--bold", "[class*='price']", "[class*='cost']", ".u-weight--bold"], "Preço não encontrado")

        return {
            'data_extracao': config.DATA_EXTRACAO,
            'titulo': titulo,
            'descricao': descricao,
            'duracao': duracao,
            'preco': preco,
            'url_detalhes': url_detalhes,
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index_str}: {e}")
        return None

def main():
    logger.info("Iniciando Journey Latin America")

    TABLE_NAME = "Journey_Latin_America"
    TABLE_SCHEMA = """
        data_extracao DATE,
        titulo VARCHAR,
        descricao TEXT,
        duracao VARCHAR,
        preco VARCHAR,
        url_detalhes VARCHAR
    """
    FIELDS = ["titulo", "descricao", "duracao", "preco", "url_detalhes"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()

    try:
        url = "https://www.journeylatinamerica.com/destinations/brazil/holidays"
        logger.info(f"Acessando: {url}")
        driver.get(url)

        WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.o-card__content"))
        )

        todos_resultados = []
        pagina_atual = 1
        max_paginas = 10

        while pagina_atual <= max_paginas:
            logger.info(f"Processando página {pagina_atual}")

            try:
                WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.o-card__content"))
                )
                time.sleep(3)
            except:
                logger.warning(f"Timeout esperando cards na página {pagina_atual}. Interrompendo.")
                break

            cards = scroll_e_carregar_cards(driver)

            if not cards:
                logger.info("Nenhum card encontrado nesta página. Interrompendo.")
                break

            resultados_pagina = []

            for index, card in enumerate(cards, 1):
                card_id = f"P{pagina_atual}-C{index}"
                resultado = extrair_dados_card(card, card_id, driver)
                if resultado and resultado['titulo'] != "Título não encontrado":
                    resultados_pagina.append(resultado)
                time.sleep(0.2)

            todos_resultados.extend(resultados_pagina)
            logger.info(f"Página {pagina_atual}: {len(resultados_pagina)} cards extraídos")

            botao_next = verificar_proxima_pagina(driver)

            if botao_next:
                logger.info("Indo para a próxima página...")
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_next)
                    time.sleep(2)

                    try:
                        driver.execute_script("arguments[0].click();", botao_next)
                    except:
                        try:
                            botao_next.click()
                        except:
                            ActionChains(driver).move_to_element(botao_next).click().perform()

                    time.sleep(5)

                    WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.o-card__content"))
                    )
                    time.sleep(2)

                    novos_cards = driver.find_elements(By.CSS_SELECTOR, "div.o-card__content")

                    if novos_cards:
                        try:
                            primeiro_novo_titulo = novos_cards[0].find_element(By.CSS_SELECTOR, "a.o-card__content__title").text.strip()
                            primeiro_titulo_anterior = resultados_pagina[0]['titulo'] if resultados_pagina else ""

                            if primeiro_novo_titulo != primeiro_titulo_anterior:
                                pagina_atual += 1
                                continue
                            else:
                                logger.info("A página não mudou (mesmo conteúdo). Interrompendo.")
                                break
                        except:
                            pagina_atual += 1
                            continue
                    else:
                        logger.warning("Clicou em 'next', mas nenhum card carregou.")
                        break

                except Exception as e:
                    logger.warning(f"Erro ao tentar clicar em 'next' ou carregar nova página: {e}")
                    break
            else:
                logger.info("Fim da paginação.")
                break

        if not todos_resultados:
            logger.warning("Nenhum resultado coletado")
            try:
                screenshot_path = f"/app/data/debug_screenshots/journey_no_results.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Screenshot salvo em: {screenshot_path}")
            except Exception as se:
                logger.error(f"Falha ao salvar screenshot: {se}")

        logger.info(f"Total de pacotes extraídos no site: {len(todos_resultados)}")

        novos_registros = []
        for r in todos_resultados:
            registro_tupla = (r['titulo'], r['descricao'], r['duracao'], r['preco'], r['url_detalhes'])
            if registro_tupla not in registros_existentes:
                novos_registros.append((
                    r['data_extracao'], r['titulo'], r['descricao'], r['duracao'],
                    r['preco'], r['url_detalhes']
                ))

        logger.info(f"Registros novos a serem inseridos: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS,
                novos_registros
            )
            logger.info(f"Dados inseridos com sucesso: {len(novos_registros)} novos registros")

            for i, reg in enumerate(novos_registros[:3], 1):
                logger.info(f"Exemplo {i}: {reg[1]} - {reg[4]}")
        else:
            logger.info("Nenhum registro novo encontrado.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total_registros}")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        try:
            screenshot_path = f"/app/data/debug_screenshots/journey_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Journey Latin America finalizado")


if __name__ == "__main__":
    main()
