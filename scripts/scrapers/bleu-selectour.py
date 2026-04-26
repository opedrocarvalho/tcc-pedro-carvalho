import sys
import os
import time
import re

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver

logger = setup_logging('bleu_selectour')


def extrair_dados_card(card, index: int) -> dict:
    try:
        titulo = "Título não encontrado"
        try:
            titulo_element = card.find_element(By.CSS_SELECTOR, "h2")
            titulo = titulo_element.text.strip()
            if not titulo:
                raise Exception("Título vazio")
        except:
            try:
                titulo_element = card.find_element(By.TAG_NAME, "h2")
                titulo = titulo_element.text.strip()
            except:
                logger.debug(f"Card {index}: Não foi possível extrair título")

        preco = "Preço não encontrado"
        try:
            price_text = card.text
            price_match = re.search(r'(\d[\d\s]*)\s*€', price_text)
            if price_match:
                preco = price_match.group(0).strip()
                logger.debug(f"Card {index}: Preço extraído via regex - {preco}")
            else:
                try:
                    price_elements = card.find_elements(By.CSS_SELECTOR, "[class*='price']")
                    for elem in price_elements:
                        text = elem.text.strip()
                        if '€' in text and text not in ['TTC/PERS', 'DÈS']:
                            preco = text
                            break
                except:
                    pass
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair preço: {e}")

        duracao = None
        try:
            card_text = card.text
            duracao_match = re.search(r'(\d+\s*jours?\s*/\s*\d+\s*nuits?)', card_text, re.IGNORECASE)
            if duracao_match:
                duracao = duracao_match.group(1).strip()
                logger.debug(f"Card {index}: Duração extraída - {duracao}")
        except Exception as e:
            logger.debug(f"Card {index}: Não foi possível extrair duração: {e}")

        tipo = None
        try:
            card_text = card.text
            if 'Séjour' in card_text:
                tipo = 'Séjour'
            elif 'Circuit' in card_text:
                tipo = 'Circuit'
            logger.debug(f"Card {index}: Tipo extraído - {tipo}")
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair tipo: {e}")

        informacoes_texto = ""
        try:
            card_text = card.text
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            info_lines = []
            skip_terms = ['DÉCOUVRIR', 'TTC/PERS', 'DÈS', '€', 'Départ de']
            for line in lines:
                if len(line) > 3 and not any(term in line for term in skip_terms):
                    if '|' in line or '•' in line or (line and line[0].islower()):
                        info_lines.append(line)
            if info_lines:
                informacoes_texto = " | ".join(info_lines[:5])
            else:
                informacoes_texto = "Informações não disponíveis"
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair informações: {e}")
            informacoes_texto = "Informações não disponíveis"

        if titulo == "Título não encontrado" or preco == "Preço não encontrado":
            logger.warning(f"Card {index}: Registro inválido (título ou preço ausente), ignorando")
            return None

        logger.debug(f"Card {index}: {titulo[:40]}... - {preco}")

        return {
            "data_extracao": config.DATA_EXTRACAO,
            "titulo": titulo,
            "preco": preco,
            "duracao": duracao,
            "tipo": tipo,
            "informacoes": informacoes_texto
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def clicar_ver_mais_offres(driver, max_clicks=20):
    clicks = 0

    for i in range(max_clicks):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            button_selectors = [
                "//a[contains(text(), 'VOIR PLUS')]",
                "//a[contains(text(), \"VOIR PLUS D'OFFRES\")]",
                "//a[contains(@class, 'see-results')]",
                "a.see-results",
                "a[class*='see-results']",
                "//button[contains(text(), 'VOIR PLUS')]"
            ]

            button_found = False
            for selector in button_selectors:
                try:
                    if selector.startswith('//'):
                        buttons = driver.find_elements(By.XPATH, selector)
                    else:
                        buttons = driver.find_elements(By.CSS_SELECTOR, selector)

                    for button in buttons:
                        try:
                            if button.is_displayed():
                                button_text = button.text.strip()
                                if 'VOIR PLUS' in button_text or 'offres' in button_text.lower():
                                    logger.info(f"Clicando no botão 'Ver mais' (clique {clicks + 1})...")
                                    logger.debug(f"  Texto do botão: {button_text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                    time.sleep(1)
                                    try:
                                        button.click()
                                    except:
                                        driver.execute_script("arguments[0].click();", button)
                                    clicks += 1
                                    button_found = True
                                    time.sleep(3)
                                    break
                        except:
                            continue

                    if button_found:
                        break

                except Exception as e:
                    logger.debug(f"Erro ao tentar seletor {selector}: {e}")
                    continue

            if not button_found:
                logger.info(f"Botão 'Ver mais' não encontrado após {clicks} cliques - todos os pacotes carregados")
                break

        except Exception as e:
            logger.debug(f"Erro ao tentar clicar em 'Ver mais': {e}")
            break

    return clicks


def main():

    logger.info("Iniciando Bleu Selectour")

    TABLE_NAME = "Bleu_Selectour"
    TABLE_SCHEMA = """
        data_extracao DATE,
        titulo VARCHAR,
        preco VARCHAR,
        duracao VARCHAR,
        tipo VARCHAR,
        informacoes VARCHAR
    """
    FIELDS = ["titulo", "preco", "duracao", "tipo", "informacoes"]

    logger.info(f"Criando/verificando tabela {TABLE_NAME}...")
    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    logger.info("Tabela criada/verificada com sucesso")

    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()

    try:
        url = "https://www.bleu-selectour.com/bresil/circuit"
        logger.info(f"Acessando: {url}")
        driver.get(url)

        logger.info("Aguardando carregamento inicial dos cards...")
        WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "col-product-card"))
        )

        time.sleep(3)

        logger.info("Carregando TODOS os pacotes disponíveis...")
        cliques = clicar_ver_mais_offres(driver, max_clicks=20)
        logger.info(f"Total de cliques em 'Ver mais': {cliques}")

        time.sleep(3)

        cards = driver.find_elements(By.CLASS_NAME, "col-product-card")
        logger.info(f"Total de cards encontrados: {len(cards)}")

        if not cards:
            logger.warning("Nenhum card encontrado. Tentando seletores alternativos...")
            cards = driver.find_elements(By.CSS_SELECTOR, "div.cpt-result-item")
            logger.info(f"Cards encontrados com seletor alternativo: {len(cards)}")

        if len(cards) < 50:
            logger.warning(f"Apenas {len(cards)} cards encontrados. Esperava-se ~53+")
            logger.warning("Pode ser necessário mais cliques no botão 'Ver mais'")

        resultados = []
        cards_validos = 0
        cards_invalidos = 0

        for index, card in enumerate(cards, 1):
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
                time.sleep(0.3)
            except:
                pass

            resultado = extrair_dados_card(card, index)

            if resultado:
                resultados.append(resultado)
                cards_validos += 1
            else:
                cards_invalidos += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"ESTATÍSTICAS DE EXTRAÇÃO:")
        logger.info(f"  Cards encontrados: {len(cards)}")
        logger.info(f"  Cards válidos extraídos: {cards_validos}")
        logger.info(f"  Cards inválidos/ignorados: {cards_invalidos}")
        logger.info(f"{'='*60}\n")

        logger.info(f"Total de pacotes extraídos: {len(resultados)}")

        novos_registros = []
        registros_duplicados = 0

        for r in resultados:
            registro_tupla = (
                r["titulo"],
                r["preco"],
                r["duracao"],
                r["tipo"],
                r["informacoes"]
            )

            if registro_tupla not in registros_existentes:
                novos_registros.append((
                    r["data_extracao"],
                    r["titulo"],
                    r["preco"],
                    r["duracao"],
                    r["tipo"],
                    r["informacoes"]
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
                logger.info(f"\nNovo registro {i}:")
                logger.info(f"  Título: {reg[1][:60]}...")
                logger.info(f"  Preço: {reg[2]}")
                logger.info(f"  Duração: {reg[3] if reg[3] else 'Não especificada'}")
                logger.info(f"  Tipo: {reg[4] if reg[4] else 'Não especificado'}")
                logger.info(f"  Info: {reg[5][:60]}...")
        else:
            logger.info("Nenhum registro novo encontrado. Todos os pacotes já existem no banco.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"\n{'='*60}")
        logger.info(f"Total de registros na tabela: {total_registros}")

        if total_registros >= 50:
            logger.info("Sucesso! Todos os pacotes foram capturados!")
        elif total_registros >= 40:
            logger.warning(f"Atenção: {total_registros} registros - pode estar faltando alguns pacotes")
        else:
            logger.error(f"Apenas {total_registros} registros - problema na extração!")

        logger.info(f"{'='*60}")

        logger.info("\n=== VERIFICAÇÃO DE QUALIDADE ===")

        campos_null = db_manager.execute_query(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN duracao IS NULL THEN 1 ELSE 0 END) as duracao_null,
                SUM(CASE WHEN tipo IS NULL THEN 1 ELSE 0 END) as tipo_null
            FROM {TABLE_NAME}
        """)

        if campos_null:
            total, duracao_null, tipo_null = campos_null[0]
            logger.info(f"Total de registros: {total}")
            logger.info(f"Duração NULL: {duracao_null} ({(duracao_null/total*100):.1f}%)")
            logger.info(f"Tipo NULL: {tipo_null} ({(tipo_null/total*100):.1f}%)")

            if duracao_null == 0 and tipo_null == 0:
                logger.info("Qualidade EXCELENTE: Todos os campos preenchidos!")
            elif duracao_null < total * 0.2 and tipo_null < total * 0.2:
                logger.info("Qualidade BOA: Menos de 20% de campos NULL")
            else:
                logger.warning("Qualidade pode ser melhorada - muitos campos NULL")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        import traceback
        logger.error(traceback.format_exc())

        try:
            screenshot_path = f"/app/data/debug_screenshots/bleu_selectour_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("\nBleu Selectour finalizado")


if __name__ == "__main__":
    main()
