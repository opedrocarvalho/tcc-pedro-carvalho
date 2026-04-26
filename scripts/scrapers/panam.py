import sys
import time

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver, tentar_encontrar_elemento

logger = setup_logging('panam')


def extrair_dados_card(card, index: int) -> dict:
    try:
        destino = "Informação não disponível"
        try:
            paragrafos = card.find_elements(By.CSS_SELECTOR, "div.booking-item-rating p")
            if not paragrafos:
                paragrafos = card.find_elements(By.CSS_SELECTOR, "p")
            
            textos = [p.text.strip() for p in paragrafos if p.text.strip() and not p.find_elements(By.TAG_NAME, "strong")]
            if textos:
                destino = " | ".join(textos) 
        except Exception as e:
            logger.debug(f"Card {index}: Não foi possível extrair informações do destino: {e}")

        preco_selectors = [
            "h5.text-color > strong",
            ".price", "[class*='price']", "h5 strong", ".text-color strong"
        ]
        preco_usd = tentar_encontrar_elemento(card, preco_selectors, "Preço não disponível")

        duracao = "Duração não disponível"
        try:
            duracao_el = card.find_element(By.CSS_SELECTOR, "p[style*='font-size:14px'] strong")
            duracao = duracao_el.text.strip()
        except Exception:
            pass

        url_destino = "URL não encontrada"
        try:
            link_element = card.find_element(By.TAG_NAME, "a")
            url_destino = link_element.get_attribute("href") or ""
        except Exception:
            pass

        logger.debug(f"Card {index}: {destino[:50]}... - Duração: {duracao} - Preço: {preco_usd}")

        return {
            "data_extracao": config.DATA_EXTRACAO,
            "destino": destino,
            "duracao": duracao,
            "preco_usd": preco_usd,
            "url": url_destino
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index}: {e}")
        return None


def main():
    logger.info("Iniciando Panam")

    TABLE_NAME = "Panam"
    TABLE_SCHEMA = """
        data_extracao DATE,
        destino VARCHAR,
        duracao VARCHAR,
        preco_usd VARCHAR,
        url VARCHAR
    """
    FIELDS = ["destino", "duracao", "preco_usd", "url"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()
    wait = WebDriverWait(driver, config.DEFAULT_TIMEOUT)

    try:
        logger.info("Acessando o site da Panam...")
        driver.get("https://www.panam.cl/")
        
        try:
            cookie_btn = wait.until(EC.element_to_be_clickable((By.ID, "cookie-btn")))
            cookie_btn.click()
            logger.info("Cookies aceitos")
        except Exception:
            logger.warning("Não foi possível encontrar o botão de cookies, continuando...")

        try:
            destinos_menu = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "DESTINOS")))
            driver.execute_script("arguments[0].click();", destinos_menu)
            logger.info("Clicado em DESTINOS")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Erro ao clicar em DESTINOS: {e}")
            raise 

        try:
            sudamerica_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "SUDAMÉRICA")))
            driver.execute_script("arguments[0].click();", sudamerica_link)
            logger.info("Clicado em SUDAMÉRICA")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Erro ao clicar em SUDAMÉRICA: {e}")
            raise

        try:
            select_pais = wait.until(EC.presence_of_element_located((By.ID, "paisPrograma")))
            Select(select_pais).select_by_visible_text("BRASIL")
            logger.info("Selecionou BRASIL no dropdown")
            time.sleep(5) 
        except Exception as e:
            logger.error(f"Erro ao selecionar BRASIL: {e}")
            raise
        
        selectors_to_try = [
            "div.booking-item-container", ".booking-item-container",
            "div[class*='booking-item']", "div[class*='destino']",
            ".package-item", ".tour-item"
        ]
        
        destinos = []
        for selector in selectors_to_try:
            try:
                destinos = driver.find_elements(By.CSS_SELECTOR, selector)
                if destinos:
                    logger.info(f"Encontrados {len(destinos)} destinos com o seletor: '{selector}'")
                    break
            except:
                continue
        
        if not destinos:
            logger.warning("Nenhum destino foi encontrado após a navegação.")
            try:
                screenshot_path = f"/app/data/debug_screenshots/panam_no_cards.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Screenshot salvo em: {screenshot_path}")
            except Exception as se:
                logger.error(f"Falha ao salvar screenshot: {se}")
            return 
        
        resultados = []
        for index, destino_card in enumerate(destinos, 1):
            resultado = extrair_dados_card(destino_card, index)
            if resultado and not resultado['url']:
                resultado['url'] = driver.current_url

            if resultado:
                resultados.append(resultado)
        
        logger.info(f"Total de pacotes extraídos: {len(resultados)}")
        
        novos_registros = []
        for r in resultados:
            registro_tupla = (r["destino"], r["duracao"], r["preco_usd"], r["url"])
            if registro_tupla not in registros_existentes:
                novos_registros.append((
                    r["data_extracao"], r["destino"], r["duracao"], r["preco_usd"], r["url"]
                ))
        
        logger.info(f"Novos registros a serem inseridos: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS,
                novos_registros
            )
            logger.info(f"Dados inseridos com sucesso: {len(novos_registros)} novos registros")
            
            for i, reg in enumerate(novos_registros[:3], 1):
                logger.info(f"Exemplo {i}: {reg[1][:60]}... - {reg[2]}")
        else:
            logger.info("Nenhum registro novo encontrado.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total_registros}")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        try:
            screenshot_path = f"/app/data/debug_screenshots/panam_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")
        raise
    
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Panam finalizado")

if __name__ == "__main__":
    main()