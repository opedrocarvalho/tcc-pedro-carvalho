from db_manager import DBManager
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, level="INFO")

TABLES_CONFIG = {
    'Bleu_Selectour': ['destino', 'descricao', 'duracao', 'preco'],
    'Comptoir_Des_Voyages': ['destino', 'url', 'descricao', 'duracao', 'preco'],
    'Ikarus_Tour': ['titulo', 'url', 'descricao', 'duracao', 'preco'],
    'Jetmar': ['destino', 'url', 'descricao', 'preco'],
    'Journey_Latin_America': ['destino', 'url', 'descricao', 'duracao', 'preco', 'categoria'],
    'Newmarket_Holidays': ['destino', 'url', 'descricao', 'duracao', 'preco'],
    'Panam': ['destino', 'url', 'descricao', 'preco'],
    'Sol_Ferias': ['destino', 'preco', 'url'],
    'Transalpino': ['destino', 'preco', 'descricao', 'url'],
    'Turismo_Costanera': ['destino', 'url', 'descricao', 'duracao', 'preco']
}


def verificar_todas_tabelas():
    db = DBManager()
    
    total_duplicatas = 0
    
    for table_name, columns in TABLES_CONFIG.items():
        try:
            stats = db.check_duplicates(table_name, columns)
            
            if stats:
                logger.info(f"\nTabela: {table_name}")
                logger.info(f"   Total de registros: {stats['total_registros']}")
                logger.info(f"   Registros únicos: {stats['registros_unicos']}")
                logger.info(f"   Duplicatas: {stats['duplicatas']}")
                
                if stats['tem_duplicatas']:
                    logger.warning(f" {stats['duplicatas']} duplicatas encontradas!")
                    total_duplicatas += stats['duplicatas']
                else:
                    logger.success(f" Sem duplicatas")
                    
        except Exception as e:
            logger.error(f" Erro ao verificar {table_name}: {e}")
    
    if total_duplicatas > 0:
        logger.warning(f"TOTAL DE DUPLICATAS NO SISTEMA: {total_duplicatas}")
    else:
        logger.success("SISTEMA SEM DUPLICATAS!")
    
    db.close()
    return total_duplicatas


def remover_duplicatas_tabela(table_name: str, keep: str = 'first'):
    if table_name not in TABLES_CONFIG:
        logger.error(f"Tabela '{table_name}' não encontrada na configuração!")
        return
    
    db = DBManager()
    columns = TABLES_CONFIG[table_name]
    
    logger.info(f"\nRemovendo duplicatas de '{table_name}'...")
    logger.info(f"   Mantendo: {keep} registro de cada grupo duplicado")
    
    stats_antes = db.check_duplicates(table_name, columns)
    
    if not stats_antes['tem_duplicatas']:
        logger.info(f" Tabela já está limpa (sem duplicatas)")
        db.close()
        return
    
    db.remove_duplicates(table_name, columns, keep)
    
    stats_depois = db.check_duplicates(table_name, columns)
    
    logger.success(f"Duplicatas removidas com sucesso!")
    logger.info(f"   Antes: {stats_antes['total_registros']} registros")
    logger.info(f"   Depois: {stats_depois['total_registros']} registros")
    logger.info(f"   Removidos: {stats_antes['duplicatas']} duplicatas")
    
    db.close()


def remover_todas_duplicatas(keep: str = 'first'):
    
    for table_name in TABLES_CONFIG.keys():
        try:
            remover_duplicatas_tabela(table_name, keep)
        except Exception as e:
            logger.error(f"Erro ao processar {table_name}: {e}")


def menu_interativo():
    while True:
        print("\n1. Verificar duplicatas em todas as tabelas")
        print("2. Remover duplicatas de uma tabela específica")
        print("3. Remover duplicatas de TODAS as tabelas")
        print("4. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == "1":
            verificar_todas_tabelas()
            
        elif opcao == "2":
            print("\nTabelas disponíveis:")
            for i, table in enumerate(TABLES_CONFIG.keys(), 1):
                print(f"{i}. {table}")
            
            tabela_num = input("\nNúmero da tabela: ").strip()
            try:
                tabela_idx = int(tabela_num) - 1
                table_name = list(TABLES_CONFIG.keys())[tabela_idx]
                
                keep = input("\nManter qual registro? (first/last) [first]: ").strip() or 'first'
                remover_duplicatas_tabela(table_name, keep)
                
            except (ValueError, IndexError):
                logger.error("Opção inválida!")
                
        elif opcao == "3":
            confirmacao = input("\nRemover duplicatas de todas as tabelas? (sim/não): ").strip().lower()
            if confirmacao == 'sim':
                keep = input("\nManter qual registro? (first/last) [first]: ").strip() or 'first'
                remover_todas_duplicatas(keep)
            else:
                logger.info("Operação cancelada")
                
        elif opcao == "4":
            logger.info("Saindo...")
            break
            
        else:
            logger.error("Opção inválida!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "verificar":
            verificar_todas_tabelas()
            
        elif comando == "limpar":
            keep = sys.argv[2] if len(sys.argv) > 2 else 'first'
            remover_todas_duplicatas(keep)
            
        else:
            print("Uso: python verificar_duplicatas.py [verificar|limpar]")
    else:
        menu_interativo()