import os
import re
import time
from playwright.sync_api import sync_playwright

# Configurações de acesso (utiliza variáveis de ambiente se disponíveis)
USUARIO = os.getenv("SISTEMA_USUARIO", "seu_usuario_aqui")
SENHA = os.getenv("SISTEMA_SENHA", "sua_senha_aqui")


def garantir_login(page):
  """Verifica se o sistema deslogou e faz o login automático se necessário."""
  try:
    if page.locator("input[type='password']").is_visible(timeout=2000):
      print(
          "\n[Aviso] Sessão expirada detectada! Efetuando re-login automático..."
      )
      page.locator(
          "input[type='text'], input[type='email'], input:not([type])"
      ).first.fill(USUARIO)
      page.locator("input[type='password']").first.fill(SENHA)
      page.locator(
          "button[type='submit'], input[type='submit'], button"
      ).filter(has_text="Entrar").first.click()
      page.wait_for_timeout(2000)
      print("[Sucesso] Sessão recuperada com sucesso!")
  except Exception:
    pass


def navegar_com_seguranca(page, url, timeout_ms=60000):
  """Navega para a URL com tolerância a oscilações e evento domcontentloaded."""
  for tentativa in range(1, 4):
    try:
      page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
      return True
    except Exception:
      print(
          f"[Aviso] Tentativa {tentativa}/3 de abrir {url} falhou. Tentando"
          " novamente..."
      )
      page.wait_for_timeout(2000)
  return False


def salvar_relatorio_completo(caminho, resultados_aptos, resultados_nao_aptos):
  """Reescreve o relatório atualizado com todos os dados acumulados."""
  with open(caminho, "w", encoding="utf-8") as relatorio:
    relatorio.write("RELATÓRIO DE TRIAGEM - AUTOMATIZADO (EM TEMPO REAL)\n")
    relatorio.write("=" * 95 + "\n")
    relatorio.write(
        f"--- PESSOAS APTAS (Classe B para cima) [{len(resultados_aptos)}] ---\n"
    )
    relatorio.write("Nome | CPF | Cargo | Telefone 1 | Telefone 2\n")
    relatorio.write("-" * 95 + "\n")
    for res in resultados_aptos:
      relatorio.write(res + "\n")

    relatorio.write("\n" + "=" * 95 + "\n")
    relatorio.write(
        f"--- PESSOAS NÃO APTAS (Classe C para baixo)"
        f" [{len(resultados_nao_aptos)}] ---\n"
    )
    relatorio.write("Nome | CPF | Cargo | Telefone 1 | Telefone 2\n")
    relatorio.write("-" * 95 + "\n")
    for res in resultados_nao_aptos:
      relatorio.write(res + "\n")
    relatorio.write("=" * 95 + "\n")
    relatorio.write("Fim do Relatório\n")


def rodar_triagem_lote():
  caminho_arquivo = "nomes.txt"
  caminho_resultado = "resultado_triagem.txt"

  if not os.path.exists(caminho_arquivo):
    print(f"Erro: O arquivo de entrada não foi encontrado: {caminho_arquivo}")
    return

  with open(caminho_arquivo, "r", encoding="utf-8") as f:
    linhas_brutas = [linha.strip() for linha in f.readlines() if linha.strip()]

  if not linhas_brutas:
    print("O arquivo de nomes está vazio!")
    return

  print(f"Foram encontrados {len(linhas_brutas)} registros para processar.")

  resultados_aptos = []
  resultados_nao_aptos = []

  with sync_playwright() as p:
    print("Iniciando o navegador...")
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # URL base de exemplo (substitua pela sua URL real de produção)
    url_base = "https://sistemas.exemplo.com.br"

    sucesso_inicial = navegar_com_seguranca(page, url_base)

    if sucesso_inicial:
      page.wait_for_timeout(2000)
      garantir_login(page)
    else:
      print("Não foi possível carregar a página inicial automaticamente.")
      input("Faça o login manualmente no navegador e pressione ENTER...")

    for index, linha in enumerate(linhas_brutas, start=1):
      partes = linha.split(",")
      nome_pesquisa = partes[0].strip()
      cargo_informado = partes[1].strip() if len(partes) > 1 else "Não informado"

      print(
          f"\n--- [{index}/{len(linhas_brutas)}] Processando:"
          f" {nome_pesquisa} | Cargo: {cargo_informado} ---"
      )

      try:
        navegar_com_seguranca(page, f"{url_base}/inicio")
        garantir_login(page)

        # ETAPA A: Consulta por Nome
        tempo_inicio_nome = time.time()
        page.get_by_text("Consulta Nome", exact=True).click()

        campo_busca = page.locator("input").first
        campo_busca.click()
        campo_busca.fill(nome_pesquisa)
        campo_busca.press("Enter")

        try:
          page.wait_for_function(
              r"() => document.body.innerText.match(/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}/)",
              timeout=20000,
          )
        except Exception:
          pass

        texto_resultados = page.inner_text("body")
        duracao_nome = time.time() - tempo_inicio_nome
        print(f"Busca por nome concluída em {duracao_nome:.2f} segundos")

        padrao_cpf = r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}"
        cpfs_encontrados = re.findall(padrao_cpf, texto_resultados)

        if not cpfs_encontrados:
          print(f"CPF não encontrado para o nome: {nome_pesquisa}")
          continue

        cpf_alvo = cpfs_encontrados[0]
        print(f"[CPF Localizado] {cpf_alvo}")

        # ETAPA B: Consulta detalhada por CPF
        tempo_inicio_cpf = time.time()
        navegar_com_seguranca(page, f"{url_base}/inicio")
        garantir_login(page)

        page.get_by_text("Consulta CPF", exact=True).click()

        campo_cpf = page.locator("input").first
        campo_cpf.click()
        campo_cpf.fill(cpf_alvo)
        campo_cpf.press("Enter")

        try:
          page.wait_for_function(
              "() => document.body.innerText.includes('Celulares') ||"
              " document.body.innerText.includes('Classe')",
              timeout=30000,
          )
        except Exception:
          pass

        page.wait_for_timeout(1000)

        dados_detalhados = page.inner_text("body")
        duracao_cpf = time.time() - tempo_inicio_cpf
        print(f"Consulta de CPF concluída em {duracao_cpf:.2f} segundos")

        # Filtro de Classe
        dados_upper = dados_detalhados.upper()
        is_classe_c_inferior = any(
            c in dados_upper
            for c in ["CLASSE C", "CLASSE D", "CLASSE E", "PADRÃO C", "PADRÃO D"]
        )
        is_classe_superior = any(
            c in dados_upper for c in ["CLASSE A", "CLASSE B", "PADRÃO A", "PADRÃO B"]
        )

        apto = True
        if is_classe_c_inferior and not is_classe_superior:
          apto = False

        # Extração de Telefones com Regex
        padrao_tel = r"\(\d{2}\)[\s\n]*9\d{4}[-\s\n]?\d{4}"
        telefones_brutos = re.findall(padrao_tel, dados_detalhados)

        telefones_unicos = []
        for tel in telefones_brutos:
          tel_limpo = " ".join(tel.split())
          if tel_limpo not in telefones_unicos:
            telefones_unicos.append(tel_limpo)

        tel1 = (
            telefones_unicos[0] if len(telefones_unicos) > 0 else "Não informado"
        )
        tel2 = (
            telefones_unicos[1] if len(telefones_unicos) > 1 else "Não informado"
        )

        print(f"Telefones capturados -> Tel 1: {tel1} | Tel 2: {tel2}")

        linha_resultado = (
            f"{nome_pesquisa} | {cpf_alvo} | {cargo_informado} | {tel1} | {tel2}"
        )

        if apto:
          resultados_aptos.append(linha_resultado)
          print("Status: APTO (Adicionado ao relatório)")
        else:
          resultados_nao_aptos.append(linha_resultado)
          print("Status: NÃO APTO (Adicionado ao relatório)")

        salvar_relatorio_completo(
            caminho_resultado, resultados_aptos, resultados_nao_aptos
        )

      except Exception as e:
        print(f"Erro ao processar {nome_pesquisa}: {e}")
        continue

    print(f"\n=== TRIAGEM COMPLETA CONCLUÍDA! ===")
    print(f"Relatório gerado em: {caminho_resultado}")

    input("Pressione ENTER para fechar o navegador.")
    browser.close()


if __name__ == "__main__":
  rodar_triagem_lote()
