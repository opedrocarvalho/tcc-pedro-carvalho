import sys
import time
sys.path.append('/app/scripts/utils')
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver

logger = setup_logging('newmarket_holidays')


def aceitar_cookies(driver):
    try:
        cookie_selectors = [
            "[class*='accept']", "[class*='agree']", "[id*='cookie']",
            "[id*='consent']", ".cookie-accept", "#accept-cookies",
            "button[class*='accept']", "[class*='cookie-banner'] button"
        ]

        for selector in cookie_selectors:
            try:
                cookie_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].click();", cookie_btn)
                logger.info("Cookies aceitos")
                time.sleep(2)
                return True
            except:
                continue
    except Exception as e:
        logger.warning(f"Não foi possível aceitar os cookies: {e}")

    logger.info("Nenhum banner de cookie encontrado ou aceito.")
    return False

def scroll_e_carregar_holidays(driver, timeout=30):

    end_time = time.time() + timeout
    holidays_anteriores = 0

    while time.time() < end_time:
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)

        try:
            load_more_selectors = [
                "button[class*='load']", "[class*='load-more']",
                "button[class*='more']", "[class*='show-more']"
            ]
            for selector in load_more_selectors:
                try:
                    load_more = driver.find_element(By.CSS_SELECTOR, selector)
                    if load_more.is_displayed():
                        driver.execute_script("arguments[0].click();", load_more)
                        logger.info("Clicado em 'carregar mais'.")
                        time.sleep(3)
                        break
                except:
                    continue
        except:
            pass

    holidays = []

    try:
        holidays = driver.find_elements(By.CSS_SELECTOR, "div.card.holiday-listing")
        if holidays:
            logger.info(f"Encontrados {len(holidays)} cards (div.card.holiday-listing)")
            return holidays
    except Exception as e:
        logger.debug(f"Seletor principal falhou: {e}")

    try:
        grid = driver.find_element(By.CSS_SELECTOR, "div.grid[data-layout-mode='grid']")
        holidays = grid.find_elements(By.CSS_SELECTOR, "div.card")
        if holidays:
            logger.info(f"Encontrados {len(holidays)} cards (dentro do grid)")
            return holidays
    except Exception as e:
        logger.debug(f"Fallback 1 falhou: {e}")

    try:
        holidays = driver.find_elements(By.CSS_SELECTOR, ".holiday-listing")
        if holidays:
            logger.info(f"Encontrados {len(holidays)} cards (.holiday-listing)")
            return holidays
    except Exception as e:
        logger.debug(f"Fallback 2 falhou: {e}")

    logger.warning("Nenhum card encontrado!")
    return holidays

def extrair_dados_holiday(holiday, index: int, driver) -> dict:
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", holiday)
        time.sleep(0.3)

        card_full_text = ""
        try:
            card_full_text = holiday.text
        except:
            pass

        titulo = ""
        url = ""
        try:
            titulo_elem = holiday.find_element(
                By.XPATH, ".//a[contains(@class, 't-h4') and contains(@href, '/destinations/')]"
            )
            titulo = titulo_elem.text.strip()
            url = titulo_elem.get_attribute("href") or ""
        except Exception as e:
            logger.debug(f"Erro ao extrair título do card {index}: {e}")

        if url and not url.startswith("http"):
            url = f"https://www.newmarketholidays.co.uk{url}"

        preco = ""
        try:
            preco_elem = holiday.find_element(By.CSS_SELECTOR, "span.price_current.text-navy-blue")
            preco = preco_elem.text.strip()
        except:
            try:
                preco_elem = holiday.find_element(By.CSS_SELECTOR, "span.price_current")
                preco = preco_elem.text.strip()
            except:
                try:
                    preco_container = holiday.find_element(By.CSS_SELECTOR, "div.holiday-listing_price")
                    preco_text = preco_container.text.strip()
                    lines = preco_text.split('\n')
                    for line in lines:
                        if '£' in line:
                            preco = line.strip()
                            break
                except:
                    if '£' in card_full_text:
                        for line in card_full_text.split('\n'):
                            if '£' in line and 'was' not in line.lower():
                                preco = line.strip()
                                break

        duracao = ""
        try:
            import re
            match = re.search(r'(\d+)\s+days?\s+from', card_full_text, re.IGNORECASE)
            if match:
                duracao = f"{match.group(1)} days"
            else:
                match = re.search(r'(\d+)\s+(day|night|week)s?', card_full_text, re.IGNORECASE)
                if match:
                    duracao = match.group(0)
        except:
            pass

        descricao = ""
        try:
            li_elements = holiday.find_elements(By.TAG_NAME, "li")
            items = [elem.text.strip() for elem in li_elements if elem.text.strip()]
            if items:
                descricao = " | ".join(items)[:500]
        except:
            pass

        logger.debug(f"Card {index}:")
        logger.debug(f"  Título: '{titulo}'")
        logger.debug(f"  Preço: '{preco}'")
        logger.debug(f"  URL: {bool(url)}")
        logger.debug(f"  Duração: '{duracao}'")

        if not titulo and not preco:
            logger.warning(f"Card {index}: Sem título e sem preço - DESCARTANDO")
            return None

        if not titulo and preco:
            lines = card_full_text.split('\n')
            for line in lines:
                line_clean = line.strip()
                if (line_clean and len(line_clean) > 10 and
                    '£' not in line_clean and
                    'days' not in line_clean.lower() and
                    'flights' not in line_clean.lower()):
                    titulo = line_clean
                    logger.debug(f"  Título extraído do texto geral: '{titulo}'")
                    break

        return {
            'data_extracao': config.DATA_EXTRACAO,
            'titulo': titulo or f"Holiday Package {index}",
            'url': url or "URL not found",
            'preco': preco or "Price on request",
            'duracao': duracao or "Duration not specified",
            'descricao': descricao or "No description available"
        }

    except Exception as e:
        logger.error(f"Erro no processamento do holiday {index}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None

def main():
    logger.info("Iniciando Newmarket Holidays")

    TABLE_NAME = "Newmarket_Holidays"
    TABLE_SCHEMA = """
        data_extracao DATE,
        titulo VARCHAR,
        url VARCHAR,
        preco VARCHAR,
        duracao VARCHAR,
        descricao TEXT
    """
    FIELDS = ["titulo", "url", "preco", "duracao", "descricao"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()

    try:
        url = "https://www.newmarketholidays.co.uk/destinations/south-and-central-america/brazil/"
        logger.info(f"Acessando: {url}")

        for tentativa in range(1, 4):
            try:
                driver.get(url)
                break
            except Exception as e:
                logger.warning(f"Tentativa {tentativa}/3 falhou ao carregar página: {e}")
                if tentativa == 3:
                    raise
                time.sleep(5)

        aceitar_cookies(driver)
        time.sleep(5)

        try:
            WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.key-info-item_p-2, div.key-info-list li"))
            )
            logger.info("Cards de holidays detectados")
        except:
            logger.warning("Timeout esperando cards, continuando...")

        holidays = scroll_e_carregar_holidays(driver)

        if len(holidays) == 0:
            logger.error("Nenhum card encontrado!")
            logger.debug(f"Título: {driver.title}")
            logger.debug(f"URL: {driver.current_url}")

            try:
                screenshot_path = f"/app/data/debug_screenshots/newmarket_no_cards.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Screenshot salvo: {screenshot_path}")
            except:
                pass

            return

        logger.info(f"{'='*60}")
        logger.info(f"Total de cards encontrados: {len(holidays)}")
        logger.info(f"{'='*60}")

        resultados = []
        for index, holiday in enumerate(holidays, 1):
            logger.info(f"\nProcessando Card {index}/{len(holidays)}")
            resultado = extrair_dados_holiday(holiday, index, driver)

            if resultado:
                resultados.append(resultado)
                logger.info(f"{resultado['titulo'][:60]}")
                logger.info(f"Preço: {resultado['preco']}")
            else:
                logger.warning(f"FALHOU: Card {index}")

            time.sleep(0.3)

        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTADO FINAL:")
        logger.info(f"  Cards encontrados: {len(holidays)}")
        logger.info(f"  Pacotes extraídos: {len(resultados)}")
        logger.info(f"{'='*60}\n")

        novos_registros = []
        for r in resultados:
            registro_tupla = (r['titulo'], r['url'], r['preco'], r['duracao'], r['descricao'])
            if registro_tupla not in registros_existentes:
                novos_registros.append((
                    r['data_extracao'], r['titulo'], r['url'], r['preco'], r['duracao'], r['descricao']
                ))

        logger.info(f"Registros novos a inserir: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS,
                novos_registros
            )
            logger.info(f"Dados inseridos: {len(novos_registros)} registros")

            logger.info("\nExemplos inseridos:")
            for i, reg in enumerate(novos_registros[:4], 1):
                logger.info(f"{i}. {reg[1][:50]} - {reg[3]}")
        else:
            logger.info("Nenhum registro novo.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"\nTotal na tabela: {total_registros} registros")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        import traceback
        logger.error(traceback.format_exc())

        try:
            screenshot_path = f"/app/data/debug_screenshots/newmarket_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro: {screenshot_path}")
        except:
            pass
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("\nNewmarket Holidays finalizado")


if __name__ == "__main__":
    main()
