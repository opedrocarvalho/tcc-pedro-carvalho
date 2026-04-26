import sys
import time
import re
import os

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver

logger = setup_logging('ikarus_tours')

DEBUG_MODE = os.environ.get("IKARUS_DEBUG", "0") == "1"
DEBUG_DIR = "/app/data/debug_screenshots"


def _salvar_debug_html(driver, elemento, nome_arquivo: str):
    if not DEBUG_MODE:
        return
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        html = driver.execute_script("return arguments[0].outerHTML;", elemento)
        caminho = os.path.join(DEBUG_DIR, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"[DEBUG] HTML salvo em: {caminho}")
    except Exception as e:
        logger.warning(f"[DEBUG] Falha ao salvar HTML de diagnóstico: {e}")


def _salvar_debug_screenshot(driver, nome_arquivo: str):
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        caminho = os.path.join(DEBUG_DIR, nome_arquivo)
        driver.save_screenshot(caminho)
        logger.warning(f"Screenshot salvo em: {caminho}")
    except Exception as e:
        logger.error(f"Falha ao salvar screenshot: {e}")

def aceitar_cookies(driver):
    seletores = [
        "[class*='akzeptieren']", "[class*='annehmen']", "[id*='cookie']",
        "button[class*='accept']", "[class*='zustimmen']",
        "[class*='agree']", "[id*='consent']",
        ".cookie-accept", "#cookie-accept", ".accept-cookies",
    ]
    for seletor in seletores:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
            )
            driver.execute_script("arguments[0].click();", btn)
            logger.info("Cookies aceitos")
            return True
        except Exception:
            continue

    logger.info("Nenhum banner de cookie encontrado ou aceito.")
    return False


def scroll_e_carregar_rundreisen(driver, timeout=30):

    end_time = time.time() + timeout
    total_anterior = 0

    while time.time() < end_time:
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)

        total_atual = len(
            driver.find_elements(By.CSS_SELECTOR, "div.col[id^='travel_']")
        )

        if total_atual == total_anterior and total_atual > 0:
            logger.info("Scroll finalizado — não há mais itens para carregar.")
            break

        total_anterior = total_atual

        for seletor in ["button[class*='mehr']", "[class*='load-more']",
                         "button[class*='weiter']", "[class*='show-more']"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, seletor)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    logger.info("Clicado em 'carregar mais'.")
                    time.sleep(3)
                    break
            except Exception:
                continue

    cards = driver.find_elements(By.CSS_SELECTOR, "div.col[id^='travel_']")
    logger.info(f"Total de cards encontrados após scroll: {len(cards)}")
    return cards



def _extrair_titulo_url(card_div):
    try:
        link = card_div.find_element(By.CSS_SELECTOR, "a[data-turbo='false']")
        url = link.get_attribute("href") or ""
        titulo = link.find_element(By.CSS_SELECTOR, "h3").text.strip()
        if titulo and url:
            return titulo, url
    except Exception:
        pass

    try:
        link = card_div.find_element(By.CSS_SELECTOR, "h3 a")
        titulo = link.text.strip()
        url = link.get_attribute("href") or ""
        if titulo and url:
            return titulo, url
    except Exception:
        pass

    try:
        titulo = card_div.find_element(By.CSS_SELECTOR, "h3").text.strip()
        url = card_div.find_element(By.CSS_SELECTOR, "a").get_attribute("href") or ""
        return titulo or "Nicht angegeben", url
    except Exception:
        pass

    return "Nicht angegeben", ""


def _extrair_preco(card_div):

    for seletor in [
        "span.fs-4.ff-special.fw-medium.text-brand-color-C",
        "span.text-brand-color-C",
    ]:
        try:
            span = card_div.find_element(By.CSS_SELECTOR, seletor)
            texto = span.text.strip()
            if texto:
                return texto  
        except Exception:
            continue

    for tag in ["span", "strong", "b", "div", "p"]:
        for el in card_div.find_elements(By.CSS_SELECTOR, tag):
            texto = el.text.strip()
            if "€" in texto and len(texto) < 30:
                return texto

    return "Auf Anfrage"


def _extrair_duracao(card_div):

    try:
        b_els = card_div.find_elements(By.CSS_SELECTOR, "b")
        for b in b_els:
            texto = b.text.strip()
            if re.search(r'\d+\s*(Tage?|Nächte?|Wochen?)', texto, re.IGNORECASE):
                return texto
    except Exception:
        pass

    match = re.search(
        r'(\d+)\s*(Tage?|Nächte?|Wochen?|days?|nights?|weeks?)',
        card_div.text,
        re.IGNORECASE
    )
    return match.group() if match else "Nicht angegeben"


def _extrair_descricao(card_div):
    try:
        bullets = card_div.find_elements(By.CSS_SELECTOR, "ul li")
        descricao = " | ".join(
            b.text.strip() for b in bullets if len(b.text.strip()) > 5
        )[:400]
        return descricao if descricao else "Nicht angegeben"
    except Exception:
        return "Nicht angegeben"


def extrair_dados_rundreise(card_div, index: int, driver) -> dict | None:
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            card_div
        )
        time.sleep(0.3)

        if DEBUG_MODE and index == 1:
            _salvar_debug_html(driver, card_div, "card_01.html")
            logger.info(f"[DEBUG] Texto bruto do card 1:\n{card_div.text[:500]}")

        titulo, url = _extrair_titulo_url(card_div)
        preco       = _extrair_preco(card_div)
        duracao     = _extrair_duracao(card_div)
        descricao   = _extrair_descricao(card_div)

        logger.debug(
            f"Card {index}: titulo='{titulo}' | preco='{preco}' "
            f"| duracao='{duracao}' | url='{url}'"
        )

        return {
            'data_extracao': config.DATA_EXTRACAO,
            'titulo':        titulo,
            'url':           url,
            'preco':         preco,
            'duracao':       duracao,
            'descricao':     descricao,
        }

    except Exception as e:
        logger.error(f"Erro ao processar card {index}: {e}")
        return None


def main():
    logger.info("Iniciando Ikarus Tours")

    TABLE_NAME   = "Ikarus_Tours"
    TABLE_SCHEMA = """
        data_extracao DATE,
        titulo        VARCHAR,
        url           VARCHAR,
        preco         VARCHAR,
        duracao       VARCHAR,
        descricao     TEXT
    """
    FIELDS = ["titulo", "url", "preco", "duracao", "descricao"]

    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()

    try:
        url_pagina = "https://www.ikarus.com/rundreisen-reiseziel-brasilien"
        logger.info(f"Acessando: {url_pagina}")
        driver.get(url_pagina)

        aceitar_cookies(driver)
        time.sleep(5)

        try:
            WebDriverWait(driver, config.DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.col[id^='travel_']")
                )
            )
            logger.debug("Cards iniciais carregados.")
        except Exception:
            logger.warning(
                "Cards esperados não carregaram no timeout. Continuando mesmo assim..."
            )

        rundreisen = scroll_e_carregar_rundreisen(driver)

        if not rundreisen:
            logger.warning(
                "Nenhum card encontrado com seletor principal. "
                "Tentando seletores alternativos..."
            )
            for seletor_alt in [
                "article.card", "div.card", "[class*='travel-item']",
                "div[class*='col']:has(h3)", "div[class*='item']",
            ]:
                rundreisen = driver.find_elements(By.CSS_SELECTOR, seletor_alt)
                if rundreisen:
                    logger.info(
                        f"Cards encontrados com seletor alternativo "
                        f"'{seletor_alt}': {len(rundreisen)}"
                    )
                    break

        if not rundreisen:
            logger.warning("Nenhum card encontrado. Salvando screenshot para diagnóstico.")
            _salvar_debug_screenshot(driver, "ikarus_no_cards.png")

        resultados = []
        logger.info(f"Iniciando extração de {len(rundreisen)} cards...")

        for index, card in enumerate(rundreisen, 1):
            resultado = extrair_dados_rundreise(card, index, driver)
            if resultado and resultado['url']:
                resultados.append(resultado)
            time.sleep(0.3)

        logger.info(f"Total de pacotes extraídos com sucesso: {len(resultados)}")

        novos_registros = []
        for r in resultados:
            chave = (r['titulo'], r['url'], r['preco'], r['duracao'], r['descricao'])
            if chave not in registros_existentes:
                novos_registros.append((
                    r['data_extracao'],
                    r['titulo'],
                    r['url'],
                    r['preco'],
                    r['duracao'],
                    r['descricao'],
                ))

        logger.info(f"Novos registros a serem inseridos: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS,
                novos_registros,
            )
            logger.info(
                f"Dados inseridos com sucesso: {len(novos_registros)} novos registros"
            )
            for i, reg in enumerate(novos_registros[:3], 1):
                logger.info(f"Exemplo {i}: [{reg[1]}] {reg[4]} — {reg[2]}")
        else:
            logger.info("Nenhum registro novo encontrado.")

        total = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total}")

    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        _salvar_debug_screenshot(driver, "ikarus_error.png")
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Ikarus Tours finalizado")


if __name__ == "__main__":
    main()