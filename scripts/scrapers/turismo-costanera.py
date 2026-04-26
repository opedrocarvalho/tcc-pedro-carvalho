import sys
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.append('/app/scripts/utils')

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver

logger = setup_logging('turismo_costanera')


def esperar_carregamento_sudamerica(driver, timeout=30):

    end_time = time.time() + timeout
    cards_anteriores = 0

    try:
        sudamerica_div = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "programas_sudamerica"))
        )
        logger.info("Div #programas_sudamerica encontrada")

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            sudamerica_div
        )
        time.sleep(3) 

        cards_sudamerica = []
        while time.time() < end_time:
            cards_sudamerica = driver.find_elements(By.CSS_SELECTOR, "#programas_sudamerica li.glide__slide")
            cards_atuais = len(cards_sudamerica)

            logger.debug(f"Cards carregados na seção Sudamérica: {cards_atuais}")

            if cards_atuais == cards_anteriores and cards_atuais > 0:
                logger.info("Número de cards estabilizado. Carregamento completo.")
                time.sleep(2) 
                return cards_sudamerica
            elif cards_atuais > cards_anteriores:
                cards_anteriores = cards_atuais

            try:
                driver.execute_script("arguments[0].scrollLeft += 500;", sudamerica_div)
                time.sleep(1) 
            except Exception as scroll_err:
                logger.warning(f"Não foi possível rolar o carousel: {scroll_err}")
                break 

            time.sleep(1)

        logger.warning(f"Timeout atingido. Retornando {len(cards_sudamerica)} cards encontrados.")
        return cards_sudamerica

    except Exception as e:
        logger.error(f"Erro crítico ao localizar ou processar #programas_sudamerica: {e}")
        return []


def extrair_dados_card(card, index: int, driver) -> dict:

    tentativas_maximas = 3

    for tentativa in range(tentativas_maximas):
        try:
            
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                card
            )
            time.sleep(0.5) 

            try:
                titulo_element = WebDriverWait(card, 5).until( 
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.tour_link"))
                )
                titulo = titulo_element.text.strip()
                url = titulo_element.get_attribute("href") or "Não informado"
            except Exception:
                titulo = "Não informado"
                url = "Não informado"

            try:
                preco_element = card.find_element(By.CSS_SELECTOR, "span.tour_price")
                preco = preco_element.text.strip()
            except Exception:
                preco = "Não informado"

            local = "Não informado"
            duracao = "Não informado"
            try:
                atributos = card.find_elements(By.CSS_SELECTOR, "div.tour_attribute_days")
                if len(atributos) > 0:
                    local = atributos[0].text.strip()
                if len(atributos) > 1:
                    duracao = atributos[1].text.strip()
            except Exception:
                pass 

            resultado = {
                'data_extracao': config.DATA_EXTRACAO,
                'titulo': titulo,
                'preco': preco,
                'local': local,
                'duracao': duracao,
                'url': url,
            }

            logger.debug(f"Card {index} processado com sucesso: {titulo}")
            return resultado

        except Exception as e:
            logger.warning(f"[TENTATIVA {tentativa + 1}/{tentativas_maximas}] Erro no card {index}: {e}")
            if tentativa < tentativas_maximas - 1:
                time.sleep(2)
                continue 
            else:
                logger.error(f"[ERRO FINAL] Card {index} não pôde ser processado após {tentativas_maximas} tentativas.")
                return None 

def main():
    logger.info("Iniciando Turismo Costanera")

    TABLE_NAME = "Turismo_Costanera"
    TABLE_SCHEMA = """
        data_extracao DATE,
        titulo VARCHAR,
        preco VARCHAR,
        local VARCHAR,
        duracao VARCHAR,
        url VARCHAR
    """
    FIELDS = ["titulo", "preco", "local", "duracao", "url"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()
    wait = WebDriverWait(driver, config.DEFAULT_TIMEOUT)

    try:
        url = "https://turismocostanera.cl/programas/"
        logger.info(f"Acessando: {url}")
        driver.get(url)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.glide__slide")))
        logger.info("Página carregada, aguardando carregamento dos cards da Sudamérica...")

        cards = esperar_carregamento_sudamerica(driver)
        logger.info(f"Total de cards encontrados na seção Sudamérica: {len(cards)}")

        if not cards:
            logger.warning("Nenhum card encontrado na seção Sudamérica após espera. Verificando fallback...")
            all_cards = driver.find_elements(By.CSS_SELECTOR, "li.glide__slide")
            logger.info(f"Fallback: Total de cards 'li.glide__slide' em toda a página: {len(all_cards)}")
            cards = all_cards 

        resultados = []
        cards_processados = 0
        if cards:
            for index, card in enumerate(cards, 1):
                resultado = extrair_dados_card(card, index, driver)
                if resultado and resultado['titulo'] != "Não informado": 
                    resultados.append(resultado)
                    cards_processados += 1
                time.sleep(0.1) 
        else:
            logger.error("Nenhum card encontrado na página, mesmo com fallback.")


        logger.info(f"Cards encontrados (após fallback, se aplicável): {len(cards)}")
        logger.info(f"Cards processados com sucesso e com título: {cards_processados}")
        logger.info(f"Cards ignorados ou com erro: {len(cards) - cards_processados}")

        novos_registros = []
        if resultados:
            for r in resultados:
                registro_tupla = tuple(r[f] for f in FIELDS)

                if registro_tupla not in registros_existentes:
                    novos_registros.append(
                        tuple([r['data_extracao']] + [r[f] for f in FIELDS])
                    )

        logger.info(f"Registros novos a serem inseridos: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS, 
                novos_registros
            )
            logger.info(f"Inseridos {len(novos_registros)} novos registros.")

            for i, reg in enumerate(novos_registros[:3], 1):
                logger.info(f"Exemplo {i}: {reg[1]} - {reg[2]}")
        elif resultados: 
            logger.info("Nenhum registro novo encontrado para inserir.")

        if not resultados and not cards:
            logger.error("Nenhum dado foi coletado! Verifique os seletores ou a estrutura da página.")
            try:
                screenshot_path = f"/app/data/debug_screenshots/costanera_no_results.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Screenshot salvo em: {screenshot_path}")
            except Exception as se:
                logger.error(f"Falha ao salvar screenshot: {se}")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total final de registros na tabela '{TABLE_NAME}': {total_registros}")

    except Exception as e:
        logger.error(f"Erro crítico na execução: {e}", exc_info=True) 
        try:
            screenshot_path = f"/app/data/debug_screenshots/costanera_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Turismo Costanera finalizado")


if __name__ == "__main__":
    main()