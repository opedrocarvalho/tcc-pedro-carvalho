import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

try:
    from config import config, setup_logging
    logger = setup_logging('selenium_utils') 
except ImportError:
    import logging
    logger = logging.getLogger('selenium_utils')
    logging.basicConfig(level=logging.INFO)


def create_chrome_driver():

    is_headless = config.HEADLESS
    options_list = config.CHROME_OPTIONS

    logger.info(f"Criando Chrome Driver. Headless={is_headless}")
    chrome_options = Options()
    chrome_options.page_load_strategy = "eager"

    for option in options_list:
        chrome_options.add_argument(option)

    if is_headless:
        chrome_options.add_argument("--headless")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        logger.info("Driver criado com sucesso.")
        return driver
    except Exception as e:
        logger.error(f"Erro ao criar driver: {e}")
        raise

def clicar_botao_ver_mais(driver, seletores_xpath: list, max_clicks=10, sleep_time=2):

    cliques = 0
    for _ in range(max_clicks):
        try:
            botao = None
            for seletor in seletores_xpath:
                try:
                    botao = driver.find_element(By.XPATH, seletor)
                    if botao and botao.is_displayed() and botao.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            if botao and botao.is_displayed() and botao.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView(true);", botao)
                time.sleep(0.5)
                botao.click()
                cliques += 1
                logger.info(f"Clicou em 'Ver mais' (Clique #{cliques})")
                time.sleep(sleep_time)
            else:
                logger.info("Botão 'Ver mais' não encontrado ou não está clicável. Parando.")
                break

        except Exception as e:
            logger.warning(f"Não foi possível clicar em 'Ver mais': {e}")
            break
            
    return cliques

def safe_get_text(elemento_pai, seletor: str, by=By.CSS_SELECTOR, default_text="Não encontrado"):

    try:
        elemento = elemento_pai.find_element(by, seletor)
        texto = elemento.text.strip()
        return texto if texto else default_text
    except NoSuchElementException:
        return default_text
    except Exception as e:
        logger.error(f"Erro em safe_get_text (Seletor: {seletor}): {e}")
        return default_text

def tentar_encontrar_elemento(elemento_pai, seletores_css: list, default_text="Não encontrado"):

    for seletor in seletores_css:
        try:
            elemento = elemento_pai.find_element(By.CSS_SELECTOR, seletor)
            texto = elemento.text.strip()
            if texto:
                return texto
        except NoSuchElementException:
            continue
    
    return default_text