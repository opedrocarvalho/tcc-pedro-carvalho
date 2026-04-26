import sys
import time
import re

sys.path.append('/app/scripts/utils')

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db_manager import db_manager
from config import config, setup_logging
from selenium_utils import create_chrome_driver

logger = setup_logging('sol_ferias')

BASE_URL = "https://www.solferias.pt"
ZONA_BRASIL = f"{BASE_URL}/#zona/view/59"

EXTRACT_DETALHE_JS = """
return (function() {
    var tabMap = {};
    document.querySelectorAll('.pageContentTabItem').forEach(function(tab) {
        var h2 = tab.querySelector('h2.pageContentTitle');
        if (h2) {
            var key = h2.innerText.trim().toLowerCase()
                        .replace(/\\s+/g, '_')
                        .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
            tabMap[key] = tab;
        }
    });

    var prog  = tabMap['programa'];
    var sobre = tabMap['sobre_o_destino'];

    var progText = prog ? prog.innerText : '';

    var rawTitle = document.querySelector('h1.pageHeaderTitlePlace')
                   ? document.querySelector('h1.pageHeaderTitlePlace').innerText.trim() : '';
    var codigoMatch = rawTitle.match(/^(\\d+)/);
    var codigo  = codigoMatch ? codigoMatch[1] : '';
    var titulo  = rawTitle.replace(/^\\d+\\s*\\n?/, '').trim();

    var precoMatch    = progText.match(/DESDE\\s*([\\d.,]+€)/i);
    var hashMatch     = location.hash.match(/\\/(\\d+)$/);

    var descricao = 'N/D';
    if (sobre) {
        descricao = sobre.innerText.replace(/Sobre o destino/i, '').trim().substring(0, 500);
    }

    return {
        id_pacote: hashMatch     ? hashMatch[1]             : '',
        codigo:    codigo,
        titulo:    titulo,
        preco:     precoMatch    ? precoMatch[1]            : 'N/D',
        descricao: descricao
    };
})();
"""


def get_destinos(driver):
    logger.info(f"Acessando listagem de destinos: {ZONA_BRASIL}")
    driver.set_page_load_timeout(60)
    try:
        driver.get(ZONA_BRASIL)
    except Exception as e:
        logger.warning(f"Timeout no carregamento da página (SPA pesada), tentando continuar: {e}")
        time.sleep(5)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ul.pagesListThumbnail li.itemBgBlue")
            )
        )
    except Exception as e:
        logger.warning(f"Timeout aguardando cards de destinos: {e}")

    cards = driver.find_elements(By.CSS_SELECTOR, "ul.pagesListThumbnail li.itemBgBlue")
    logger.info(f"Encontrados {len(cards)} destinos")

    destinos = []
    for card in cards:
        try:
            nome = card.find_element(By.CSS_SELECTOR, "h3.listThumbnailTitle").text.strip()

            try:
                preco = card.find_element(By.CSS_SELECTOR, "p.listThumbnailText span").text.strip()
            except Exception:
                preco = "N/D"

            href = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href") or ""

            if nome and href:
                destinos.append({"nome": nome, "preco": preco, "href": href})
                logger.debug(f"Destino: {nome} - {preco}")
        except Exception as e:
            logger.warning(f"Erro ao extrair card de destino: {e}")

    return destinos


def get_pacotes_destino(driver, url_destino):
    logger.info(f"Acessando destino:  {url_destino}")
    driver.get(url_destino)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.gpproduto"))
        )
    except Exception as e:
        logger.warning(f"Timeout aguardando pacotes do destino: {e}")
        return []

    time.sleep(2)

    cards = driver.find_elements(By.CSS_SELECTOR, "li.gpproduto")
    logger.info(f"Encontrados {len(cards)} pacotes")

    pacotes = []
    for card in cards:
        try:
            a_tag = card.find_element(By.CSS_SELECTOR, "a")
            href = a_tag.get_attribute("href") or ""

            id_match = re.search(r'/(\d+)$', href)
            if not id_match:
                continue
            id_pacote = id_match.group(1)

            try:
                nome = card.find_element(By.CSS_SELECTOR, ".pageListProdInfo h4").text.strip()
            except Exception:
                try:
                    info_el = card.find_element(By.CSS_SELECTOR, ".pageListProdInfo")
                    nome = info_el.text.split('\n')[0].strip()
                except Exception:
                    nome = "N/D"

            try:
                price_text = card.find_element(By.CSS_SELECTOR, ".pageListProdPrice").text.strip()
                noites_match = re.search(r'(\d+)\s*NOITES', price_text, re.IGNORECASE)
                preco_match  = re.search(r'([\d.,]+)€', price_text)
                duracao = noites_match.group(0) if noites_match else "N/D"
                preco   = preco_match.group(1) + "€" if preco_match else "N/D"
            except Exception:
                duracao = "N/D"
                preco   = "N/D"

            pacotes.append({
                "id":      id_pacote,
                "href":    href,
                "nome":    nome[:120],
                "duracao": duracao,
                "preco":   preco
            })
            logger.debug(f"Pacote #{id_pacote}: {nome[:50]} - {preco}")

        except Exception as e:
            logger.warning(f"Erro ao extrair card de pacote: {e}")

    return pacotes


def get_pacote_detalhe(driver, url_pacote, retries=3):
    for attempt in range(retries):
        try:
            driver.get(url_pacote)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.pageHeaderTitlePlace"))
            )
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".pageContentTabItem h2.pageContentTitle")
                )
            )
            time.sleep(1)
            return driver.execute_script(EXTRACT_DETALHE_JS)

        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 3 * (attempt + 1)
            logger.warning(f"Tentativa {attempt + 1} falhou ({e}). Aguardando {wait}s...")
            time.sleep(wait)


def main():
    logger.info("Iniciando Sol Férias")

    TABLE_NAME = "Sol_Ferias"
    TABLE_SCHEMA = """
        data_extracao DATE,
        destino       VARCHAR,
        id_pacote     VARCHAR,
        codigo        VARCHAR,
        titulo        VARCHAR,
        duracao       VARCHAR,
        preco         VARCHAR,
        descricao     TEXT,
        url           VARCHAR
    """
    FIELDS = [
        "destino", "id_pacote", "codigo", "titulo", "duracao", "preco",
        "descricao", "url"
    ]

    db_manager.delete_table(TABLE_NAME)
    db_manager.create_table(TABLE_NAME, TABLE_SCHEMA)
    registros_existentes = db_manager.get_existing_records(TABLE_NAME, FIELDS)
    logger.info(f"Registros já existentes no banco: {len(registros_existentes)}")

    driver = create_chrome_driver()
    todos_resultados = []

    try:
        destinos = get_destinos(driver)

        if not destinos:
            logger.warning("Nenhum destino encontrado. Verificando página...")
            try:
                driver.save_screenshot("/app/data/debug_screenshots/solferias_no_destinos.png")
                logger.warning("Screenshot salvo.")
            except Exception:
                pass
            return

        for destino in destinos:
            logger.info(f"Processando destino: {destino['nome']}")

            try:
                pacotes = get_pacotes_destino(driver, destino['href'])
            except Exception as e:
                logger.error(f"Erro ao listar pacotes de {destino['nome']}: {e}")
                continue

            logger.info(f"  {len(pacotes)} pacotes encontrados em {destino['nome']}")

            for pac in pacotes:
                time.sleep(1.5)  
                logger.info(f"  Extraindo pacote #{pac['id']}: {pac['nome'][:55]}")

                try:
                    detalhe = get_pacote_detalhe(driver, pac['href'])
                    if detalhe:
                        todos_resultados.append({
                            "data_extracao": config.DATA_EXTRACAO,
                            "destino":   destino['nome'],
                            "id_pacote": detalhe.get("id_pacote") or pac["id"],
                            "codigo":    detalhe.get("codigo", "N/D"),
                            "titulo":    detalhe.get("titulo") or pac["nome"],
                            "duracao":   pac["duracao"],  
                            "preco":     detalhe.get("preco") or pac["preco"],
                            "descricao": detalhe.get("descricao", "N/D"),
                            "url":       pac["href"]
                        })
                        logger.debug(
                            f"    {detalhe.get('titulo', '')[:55]} - {detalhe.get('preco', '')}"
                        )
                except Exception as e:
                    logger.error(f"  Falhou pacote #{pac['id']}: {e}")
                    try:
                        driver.save_screenshot(
                            f"/app/data/debug_screenshots/solferias_pac_{pac['id']}_error.png"
                        )
                    except Exception:
                        pass

        logger.info(f"Total de pacotes extraídos: {len(todos_resultados)}")

        novos_registros = []
        for r in todos_resultados:
            registro_tupla = tuple(r[f] for f in FIELDS)
            if registro_tupla not in registros_existentes:
                novos_registros.append(
                    tuple([r["data_extracao"]] + [r[f] for f in FIELDS])
                )

        logger.info(f"Novos registros a serem inseridos: {len(novos_registros)}")

        if novos_registros:
            db_manager.insert_records(
                TABLE_NAME,
                ["data_extracao"] + FIELDS,
                novos_registros
            )
            logger.info(f"Dados inseridos com sucesso: {len(novos_registros)} novos registros")

            for i, reg in enumerate(novos_registros[:3], 1):
                logger.info(f"Exemplo {i}: [{reg[3]}] {reg[5]} - {reg[7]}") 
        else:
            logger.info("Nenhum registro novo encontrado.")

        total_registros = db_manager.get_table_count(TABLE_NAME)
        logger.info(f"Total de registros na tabela: {total_registros}")

    except Exception as e:
        logger.error(f"Erro crítico na execução: {e}")
        try:
            driver.save_screenshot("/app/data/debug_screenshots/solferias_error.png")
            logger.warning("Screenshot de erro salvo.")
        except Exception as se:
            logger.error(f"Falha ao salvar screenshot: {se}")
        raise

    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        logger.info("Sol Férias finalizado")


if __name__ == "__main__":
    main()
