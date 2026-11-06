"""Teste automático do mural anônimo.
Roda contra uma rede já no ar (use ./iniciar_rede.sh antes).
"""
import json
import re
import sys
import time
from pathlib import Path

# Importa as funções do cliente
import cliente


# ---------- utilitários de verificação ----------

def checar(cond, mensagem):
    if cond:
        print(f"  [OK] {mensagem}")
        return True
    else:
        print(f"  [FALHOU] {mensagem}")
        return False


def contar_repassando(nome_rele):
    """Conta quantas linhas 'repassando' tem no log do relé."""
    caminho = Path("logs") / f"{nome_rele}.txt"
    if not caminho.exists():
        return 0
    texto = caminho.read_text()
    return len(re.findall(r"repassando", texto))


# ---------- testes ----------

def teste_postar_e_listar():
    print("\n=== Teste 1: postar e listar ===")
    ok = True

    # Posta
    r = cliente.enviar_ao_mural({
        "tipo": "POSTAR",
        "topico": "geral",
        "titulo": "via teste",
        "texto": "olá do teste",
        "apelido": "bot",
        "senha": "senha-do-bot",
    })
    ok &= checar(r and r.get("tipo") == "OK", f"POSTAR devolveu OK (recebido: {r})")
    if not (r and r.get("tipo") == "OK"):
        return False
    id_post = r["id"]

    # Lista
    r = cliente.enviar_ao_mural({"tipo": "LISTAR", "topico": "geral"})
    ok &= checar(r and r.get("tipo") == "POSTS", f"LISTAR devolveu POSTS")
    if r and r.get("tipo") == "POSTS":
        ids = [p["id"] for p in r["posts"]]
        ok &= checar(id_post in ids, f"post {id_post} aparece na listagem")

    return ok


def teste_ler():
    print("\n=== Teste 2: ler ===")
    ok = True
    r = cliente.enviar_ao_mural({"tipo": "LER", "id": 1})
    ok &= checar(r and r.get("tipo") == "POST", f"LER devolveu POST")
    if r and r.get("tipo") == "POST":
        ok &= checar("autor" in r, "campo 'autor' presente")
        ok &= checar("respostas" in r, "campo 'respostas' presente")
    return ok


def teste_responder():
    print("\n=== Teste 3: responder ===")
    r = cliente.enviar_ao_mural({
        "tipo": "RESPONDER",
        "id": 1,
        "texto": "resposta do bot",
        "apelido": "bot",
        "senha": "senha-do-bot",
    })
    return checar(r and r.get("tipo") == "OK", f"RESPONDER devolveu OK (recebido: {r})")


def teste_topico_inexistente():
    print("\n=== Teste 4: tópico inexistente ===")
    r = cliente.enviar_ao_mural({"tipo": "LISTAR", "topico": "nao_existe"})
    return checar(
        r and r.get("tipo") == "ERROR",
        f"devolveu ERROR (recebido: {r})",
    )


def teste_id_inexistente():
    print("\n=== Teste 5: id inexistente ===")
    r = cliente.enviar_ao_mural({"tipo": "LER", "id": 9999})
    return checar(
        r and r.get("tipo") == "ERROR",
        f"devolveu ERROR (recebido: {r})",
    )


def teste_apagar_senha_errada():
    print("\n=== Teste 6: apagar com senha errada ===")
    r = cliente.enviar_ao_mural({
        "tipo": "APAGAR",
        "id": 1,
        "senha": "senha-errada",
    })
    return checar(
        r and r.get("tipo") == "ERROR",
        f"devolveu ERROR (recebido: {r})",
    )


def teste_apagar_senha_certa():
    print("\n=== Teste 7: apagar com senha certa ===")
    r = cliente.enviar_ao_mural({
        "tipo": "APAGAR",
        "id": 1,
        "senha": "senha-do-bot",
    })
    ok = checar(r and r.get("tipo") == "OK", f"APAGAR devolveu OK (recebido: {r})")

    # Confirma que sumiu
    r = cliente.enviar_ao_mural({"tipo": "LER", "id": 1})
    ok &= checar(r and r.get("tipo") == "ERROR", "LER do post apagado devolve ERROR")
    return ok


def teste_caminho_aleatorio():
    print("\n=== Teste 8: caminho aleatório ===")
    caminhos = set()
    for _ in range(5):
        caminho = cliente.escolher_caminho()
        nomes = tuple(info["nome"] for info in caminho)
        caminhos.add(nomes)
    return checar(len(caminhos) > 1, f"caminhos diferentes em 5 sorteios: {caminhos}")


# ---------- métricas ----------

def medir_tamanhos():
    print("\n=== Métricas: tamanho do POSTAR por salto ===")
    pedido = {
        "tipo": "POSTAR",
        "topico": "geral",
        "titulo": "t",
        "texto": "x" * 100,
        "apelido": "bot",
        "senha": "s",
    }
    caminho = cliente.escolher_caminho()

    # Camada mais externa (o que o cliente envia ao R1)
    pacote, _ = cliente.montar_cebola(pedido, caminho)
    tamanho_cheio = len(json.dumps(pacote))

    # Sem o primeiro relé (simula o pacote entre R1 e R2)
    pacote_sem_r1, _ = cliente.montar_cebola(pedido, caminho[1:])
    tamanho_sem_r1 = len(json.dumps(pacote_sem_r1))

    # Só com o último relé (simula o pacote entre R2 e R3)
    pacote_ultimo, _ = cliente.montar_cebola(pedido, caminho[-1:])
    tamanho_ultimo = len(json.dumps(pacote_ultimo))

    # O pedido puro (o que chega ao mural)
    tamanho_puro = len(json.dumps(pedido))

    print(f"  Cliente → R1: {tamanho_cheio} bytes")
    print(f"  R1     → R2: {tamanho_sem_r1} bytes")
    print(f"  R2     → R3: {tamanho_ultimo} bytes")
    print(f"  R3  → mural: {tamanho_puro} bytes")
    return True


def medir_tempos(n=20):
    print(f"\n=== Métricas: tempo médio de {n} pedidos ===")
    pedido = {"tipo": "TOPICOS"}

    # Direto ao mural (bypassa o circuito)
    from comum import pedir
    t0 = time.time()
    for _ in range(n):
        pedir(cliente.MURAL, pedido)
    t_direto = (time.time() - t0) / n

    # Pelo circuito (usa o enviar_ao_mural normal)
    t0 = time.time()
    for _ in range(n):
        cliente.enviar_ao_mural(pedido)
    t_circuito = (time.time() - t0) / n

    print(f"  Direto ao mural:  {t_direto * 1000:.2f} ms por pedido")
    print(f"  Pelo circuito:    {t_circuito * 1000:.2f} ms por pedido")
    print(f"  Overhead do anonimato: {t_circuito / t_direto:.1f}x")
    return True


def contar_repasses():
    print("\n=== Contagem de repasses por pedido ===")
    # Zera os logs contando antes
    antes = {f"R{i}": contar_repassando(f"R{i}") for i in range(1, 5)}

    # Faz 1 pedido
    cliente.enviar_ao_mural({"tipo": "TOPICOS"})
    time.sleep(0.3)  # deixa os logs serem escritos

    depois = {f"R{i}": contar_repassando(f"R{i}") for i in range(1, 5)}
    deltas = {k: depois[k] - antes[k] for k in antes}
    total = sum(deltas.values())

    print(f"  Repasses por relé: {deltas}")
    print(f"  Total: {total}")
    return checar(total == 3, "exatamente 3 repasses por pedido (um por relé do circuito)")


# ---------- main ----------

def main():
    print("Rodando bateria de testes do mural anônimo...")
    print("Pré-requisito: ./iniciar_rede.sh já foi executado.")

    resultados = []
    resultados.append(("postar_e_listar", teste_postar_e_listar()))
    resultados.append(("ler", teste_ler()))
    resultados.append(("responder", teste_responder()))
    resultados.append(("topico_inexistente", teste_topico_inexistente()))
    resultados.append(("id_inexistente", teste_id_inexistente()))
    resultados.append(("apagar_senha_errada", teste_apagar_senha_errada()))
    resultados.append(("apagar_senha_certa", teste_apagar_senha_certa()))
    resultados.append(("caminho_aleatorio", teste_caminho_aleatorio()))
    resultados.append(("medir_tamanhos", medir_tamanhos()))
    resultados.append(("medir_tempos", medir_tempos()))
    resultados.append(("contar_repasses", contar_repasses()))

    print("\n=== Resumo ===")
    falhas = 0
    for nome, ok in resultados:
        status = "OK" if ok else "FALHOU"
        print(f"  {status:7s} {nome}")
        if not ok:
            falhas += 1

    if falhas == 0:
        print("\nTodas as verificações passaram.")
        sys.exit(0)
    else:
        print(f"\n{falhas} verificação(ões) falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()