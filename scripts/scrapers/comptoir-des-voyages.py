import sys
import time
sys.path.append('/app/scripts/utils')
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver

logger = setup_logging('comptoir_des_voyages')


def extrair_dados_card(card, index: int) -> dict:
    try:
        try:
            link_element = card.find_element(By.CSS_SELECTOR, "a.module__tripCard__card__link")
            destino = link_element.text.strip()
            url = link_element.get_attribute("href").strip()
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair destino/url: {e}")
            destino = "Destino não encontrado"
            url = "URL não encontrada"

        try:
            descricao_element = card.find_element(By.CSS_SELECTOR, "span")
            descricao = descricao_element.text.strip()
            if not descricao:
                descricao = "Descrição não encontrada"
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair descrição: {e}")
            descricao = "Descrição não encontrada"

        try:
            duracao_element = card.find_element(By.CSS_SELECTOR, ".module__tripCard__card__duration")
            duracao = duracao_element.text.strip()
            if not duracao:
                duracao = "Duração não encontrada"
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair duração: {e}")
            duracao = "Duração não encontrada"

        try:
            preco_element = card.find_element(By.CSS_SELECTOR, ".module__tripCard__card__price")
            preco = preco_element.text.strip()
            if not preco:
                preco = "Preço não encontrado"
        except Exception as e:
            logger.debug(f"Card {index}: Erro ao extrair preço: {e}")
            preco = "Preço não encontrado"

        logger.debug(f"Card {index}: {destino} - {preco}")

        return {
            "data_extracao": config.DATA_EXTRACAO,
            "destino": destino,
            "url": url,
            "descricao": descricao,
            "duracao": duracao,
            "preco": preco
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index}: {e}")
        return None


def main():

    logger.info("Iniciando Comptoir Des Voyages")

    TABLE_NAME = "Comptoir_Des_Voyages"
    TABLE_SCHEMA = """
        data_extracao DATE,
        destino VARCHAR,
        url VARCHAR,
        descricao VARCHAR,
        duracao VARCHAR,
        preco VARCHAR
    """
    FIELDS = ["destino", "url", "descricao", "duracao", "preco"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()

    try:
        url = "https://www.comptoirdesvoyages.fr/voyage-pays/bresil/bra"
        logger.info(f"Acessando: {url}")
        driver.get(url)

        WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".module__tripCard__card__content"))
        )

        time.sleep(3)

        cards = driver.find_elements(By.CSS_SELECTOR, ".module__tripCard__card__content")
        logger.info(f"Total de cards encontrados: {len(cards)}")

        if not cards:
            logger.warning("Nenhum card encontrado. Tentando seletor alternativo...")
            cards = driver.find_elements(By.CSS_SELECTOR, "div.module__tripCard__card")
            logger.info(f"Cards encontrados com seletor alternativo: {len(cards)}")

        resultados = []
        for index, card in enumerate(cards, 1):
            resultado = extrair_dados_card(card, index)
            if resultado and resultado["destino"] != "Destino não encontrado":
                resultados.append(resultado)
            time.sleep(0.2)

        logger.info(f"Total de pacotes extraídos: {len(resultados)}")

        novos_registros = []
        for r in resultados:
            registro_tupla = (r["destino"], r["url"], r["descricao"], r["duracao"], r["preco"])
            if registro_tupla not in registros_existentes:
                novos_registros.append((
                    r["data_extracao"],
                    r["destino"],
                    r["url"],
                    r["descricao"],
                    r["duracao"],
                    r["preco"]
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
                logger.info(f"Exemplo {i}: {reg[1]} - {reg[5]}")
        else:
            logger.info("Nenhum registro novo encontrado. Banco de dados já está atualizado.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total_registros}")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        try:
            screenshot_path = f"/app/data/debug_screenshots/comptoir_error.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Screenshot de erro salvo em: {screenshot_path}")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot de erro: {se}")
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Comptoir Des Voyages finalizado")


if __name__ == "__main__":
    main()
