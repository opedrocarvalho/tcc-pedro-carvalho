import sys
import time

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver, tentar_encontrar_elemento

logger = setup_logging('transalpino')


def extrair_dados_card(card, index: int, page_url: str) -> dict:
    try:
        destino = tentar_encontrar_elemento(card, [".item-title"], "Destino não encontrado")
        
        preco = "Preço não encontrado"
        try:
            preco_elements = card.find_elements(By.CSS_SELECTOR, ".item-price")
            
            for elem in preco_elements:
                try:
                    span = elem.find_element(By.TAG_NAME, "span")
                    preco_texto = span.text.strip()
                    if preco_texto and preco_texto.isdigit():
                        preco = f"{preco_texto}€"
                        break
                except:
                    continue
            
            if preco == "Preço não encontrado":
                for elem in preco_elements:
                    texto = elem.text.strip()
                    if '€' in texto or texto.isdigit():
                        texto_limpo = texto.replace('Desde', '').replace('==', '').strip()
                        if texto_limpo:
                            preco = texto_limpo
                            break
        except Exception as e:
            logger.debug(f"Erro ao extrair preço do card {index}: {e}")
        

        try:
            desc1 = card.find_element(By.CSS_SELECTOR, ".item-descr").text.strip()
        except Exception:
            desc1 = ""
        

        try:
            desc2 = card.find_element(By.CSS_SELECTOR, ".item-desc").text.strip()
        except Exception:
            desc2 = ""
        
        descricao = f"{desc1} {desc2}".strip()
        if not descricao:
            descricao = "Descrição não encontrada"

        url_pacote = page_url
        try:
            link_element = card.find_element(By.CSS_SELECTOR, "a.item-image")
            url_pacote = link_element.get_attribute("href")
            if url_pacote:
                url_pacote = url_pacote.strip()
        except Exception:
            
            pass

        logger.debug(f"Card {index}: {destino} - {preco}")

        return {
            "data_extracao": config.DATA_EXTRACAO,
            "destino": destino,
            "preco": preco,
            "descricao": descricao,
            "url": url_pacote
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index}: {e}")
        return None


def main():
    logger.info("Iniciando Transalpino")

    TABLE_NAME = "Transalpino"
    TABLE_SCHEMA = """
        data_extracao DATE,
        destino VARCHAR,
        preco VARCHAR,
        descricao VARCHAR,
        url VARCHAR
    """
    FIELDS = ["destino", "preco", "descricao", "url"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    urls = [
        "https://www.transalpino.pt/cat/5-praias/",
        "https://www.transalpino.pt/cat/3-cruzeiros/",
        "https://www.transalpino.pt/cat/1-pacotes/",
        "https://www.transalpino.pt/cat/4-lua-de-mel/",
        "https://www.transalpino.pt/cat/9-cidades/" 
    ]
    
    driver = create_chrome_driver()
    todos_resultados = []

    try:
        for url in urls:
            logger.info(f"Acessando categoria: {url}")
            
            try:
                driver.set_page_load_timeout(30)
                driver.get(url)
                
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Timeout ao carregar página {url}: {e}")
                logger.warning(f"Pulando categoria {url}")
                continue
            
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card"))
                )
            except Exception as e:
                logger.warning(f"Timeout esperando cards em {url}. Tentando continuar... ({e})")
            
            cards = driver.find_elements(By.CSS_SELECTOR, "div.card")
            
            if len(cards) == 0:
                cards = driver.find_elements(By.CSS_SELECTOR, "div.item")
            
            if len(cards) == 0:
                logger.warning(f"Nenhum card encontrado em {url}, pulando.")
                continue

            logger.info(f"Encontrados {len(cards)} cards em {url}")

            resultados_pagina = []
            for index, card in enumerate(cards, 1):
                resultado = extrair_dados_card(card, index, url)
                if resultado and resultado["destino"] != "Destino não encontrado":
                    resultados_pagina.append(resultado)
            
            todos_resultados.extend(resultados_pagina)
            logger.info(f"Extraídos {len(resultados_pagina)} pacotes de {url}")
            
            time.sleep(2)
                
        logger.info(f"Total de pacotes extraídos no site: {len(todos_resultados)}")
        
        novos_registros = []
        for r in todos_resultados:
            registro_tupla = (r["destino"], r["preco"], r["descricao"], r["url"])
            if registro_tupla not in registros_existentes:
                novos_registros.append((
                    r["data_extracao"], r["destino"], r["preco"],
                    r["descricao"], r["url"]
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
                logger.info(f"Exemplo {i}: {reg[1]} - {reg[2]}")
        else:
            logger.info("Nenhum registro novo encontrado.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total_registros}")

    except Exception as e:
        logger.error(f"Erro crítico na execução: {e}")
        try:
            screenshot_path = f"/app/data/debug_screenshots/transalpino_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")
        
        logger.warning("Continuando com os dados coletados até o momento...")
    
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Transalpino finalizado")


if __name__ == "__main__":
    main()