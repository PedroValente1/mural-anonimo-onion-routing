import socket
import random
from comum import (
    pedir, nova_chave, cifrar, decifrar,
    cifrar_rsa, decifrar_rsa,
)


MURAL = "127.0.0.1:7000"
DIRETORIO = "127.0.0.1:9000"


def enviar_ao_mural(pedido):
    caminho = escolher_caminho()
    pacote, chaves = montar_cebola(pedido, caminho)
    resposta_cifrada = pedir(caminho[0]["endereco"], pacote)
    return abrir_resposta(resposta_cifrada, caminho, chaves)


def perguntar(texto):
    """input que trata Ctrl+C para não fechar o programa."""
    try:
        return input(texto).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def mostrar_topicos():
    resposta = enviar_ao_mural({"tipo": "TOPICOS"})
    if resposta is None or resposta["tipo"] == "ERROR":
        print(f"Erro: {resposta['motivo'] if resposta else 'sem resposta'}")
        return None
    for i, topico in enumerate(resposta["lista"], start=1):
        print(f"  {i}. {topico}")
    return resposta["lista"]


def mostrar_posts_de(topico):
    resposta = enviar_ao_mural({"tipo": "LISTAR", "topico": topico})
    if resposta is None or resposta["tipo"] == "ERROR":
        print(f"Erro: {resposta['motivo'] if resposta else 'sem resposta'}")
        return
    if not resposta["posts"]:
        print(f"  (tópico '{topico}' está vazio)")
        return
    for p in resposta["posts"]:
        print(f"  [{p['id']}] {p['titulo']} — por {p['autor']} ({p['respostas']} respostas)")


def ler_post(id_post):
    resposta = enviar_ao_mural({"tipo": "LER", "id": id_post})
    if resposta is None or resposta["tipo"] == "ERROR":
        print(f"Erro: {resposta['motivo'] if resposta else 'sem resposta'}")
        return
    print("\n--- post ---")
    print(f"por {resposta['autor']}")
    print(resposta["texto"])
    print("--- respostas ---")
    if not resposta["respostas"]:
        print("  (sem respostas)")
    for r in resposta["respostas"]:
        print(f"  {r['apelido']}: {r['texto']}")
    print("-------------\n")


def opcao_topicos():
    print("\nTópicos disponíveis:")
    mostrar_topicos()


def opcao_listar(apelido):
    topico = perguntar("Tópico: ")
    if not topico:
        return
    print(f"\nPosts em '{topico}':")
    mostrar_posts_de(topico)


def opcao_apagar(senha):
    entrada = perguntar("id do post a apagar: ")
    if not entrada:
        return
    try:
        id_post = int(entrada)
    except ValueError:
        print("id inválido")
        return
    if not senha:
        print("Você não tem senha definida; não é possível apagar.")
        return
    pedido = {"tipo": "APAGAR", "id": id_post, "senha": senha}
    resposta = enviar_ao_mural(pedido)
    if resposta is None or resposta["tipo"] == "ERROR":
        print(f"Erro: {resposta['motivo'] if resposta else 'sem resposta'}")
        return
    print("Post apagado.")


def opcao_ler():
    entrada = perguntar("id do post: ")
    if not entrada:
        return
    try:
        id_post = int(entrada)
    except ValueError:
        print("id inválido")
        return
    ler_post(id_post)


def opcao_postar(apelido, senha):
    topico = perguntar("Tópico: ")
    if not topico:
        return
    titulo = perguntar("Título: ")
    if titulo is None:
        return
    texto = perguntar("Texto: ")
    if texto is None:
        return
    pedido = {
        "tipo": "POSTAR",
        "topico": topico,
        "titulo": titulo,
        "texto": texto,
        "apelido": apelido,
        "senha": senha,
    }
    resposta = enviar_ao_mural(pedido)
    if resposta is None or resposta["tipo"] == "ERROR":
        print(f"Erro: {resposta['motivo'] if resposta else 'sem resposta'}")
        return
    print(f"Post criado com id {resposta['id']}")


def opcao_responder(apelido, senha):
    entrada = perguntar("id do post: ")
    if not entrada:
        return
    try:
        id_post = int(entrada)
    except ValueError:
        print("id inválido")
        return
    texto = perguntar("Texto da resposta: ")
    if texto is None:
        return
    pedido = {
        "tipo": "RESPONDER",
        "id": id_post,
        "texto": texto,
        "apelido": apelido,
        "senha": senha,
    }
    resposta = enviar_ao_mural(pedido)
    if resposta is None or resposta["tipo"] == "ERROR":
        print(f"Erro: {resposta['motivo'] if resposta else 'sem resposta'}")
        return
    print("Resposta publicada.")


def menu():
    apelido = perguntar("Seu apelido: ") or "anônimo"
    senha = perguntar("Senha de autor (pode ficar vazia): ") or ""
    print(f"\nBem-vindo, {apelido}!")

    while True:
        print("\n=== Mural Anônimo ===")
        print("1. Ver tópicos")
        print("2. Listar tópico")
        print("3. Ler post")
        print("4. Postar")
        print("5. Responder")
        print("6. Apagar post")
        print("7. Sair")

        opcao = perguntar("Opção: ")
        if opcao is None or opcao == "7":
            print("Tchau.")
            break

        try:
            if opcao == "1":
                opcao_topicos()
            elif opcao == "2":
                opcao_listar(apelido)
            elif opcao == "3":
                opcao_ler()
            elif opcao == "4":
                opcao_postar(apelido, senha)
            elif opcao == "5":
                opcao_responder(apelido, senha)
            elif opcao == "6":
                opcao_apagar(senha)
            else:
                print("opção inválida")
        except (OSError, socket.timeout) as e:
            print(f"Erro de rede: {e}")
            print("O mural está rodando? Tente de novo.")
        except RuntimeError as e:
            # Falha no circuito (relé ou mural fora do ar, poucos relés)
            print(f"Erro no circuito: {e}")
            print("Tente de novo; um novo caminho será sorteado.")


def montar_cebola(pedido, caminho_reles):
    """Monta a cebola cifrada de dentro para fora.
    caminho_reles é uma lista de dicts {nome, endereco, chave_publica}.
    Devolve (pacote_externo, chaves_por_endereco)."""
    conteudo = pedido
    proximo = MURAL
    chaves = {}

    # Itera do ÚLTIMO relé para o PRIMEIRO
    for info in reversed(caminho_reles):
        endereco_rele = info["endereco"]
        chave_fernet = nova_chave()
        chaves[endereco_rele] = chave_fernet

        corpo = {"proximo": proximo, "conteudo": conteudo}
        dados_cifrados = cifrar(chave_fernet, corpo)
        chave_cifrada = cifrar_rsa(info["chave_publica"], chave_fernet)

        conteudo = {
            "tipo": "CEBOLA",
            "chave": chave_cifrada,
            "dados": dados_cifrados,
        }
        proximo = endereco_rele

    return conteudo, chaves


def obter_reles():
    """Pede ao diretório a lista de relés registrados."""
    resposta = pedir(DIRETORIO, {"tipo": "LISTAR_RELES"})
    if resposta is None or resposta.get("tipo") != "RELES":
        raise RuntimeError(f"diretório indisponível: {resposta}")
    return resposta["lista"]


def escolher_caminho():
    """Sorteia 3 relés diferentes."""
    lista = obter_reles()
    if len(lista) < 3:
        raise RuntimeError(f"preciso de 3 relés, tenho {len(lista)}")
    return random.sample(lista, 3)


def abrir_resposta(pacote, caminho_reles, chaves):
    """A resposta vem cifrada com cada chave, R1 por fora.
    Decifra na ordem R1, R2, R3."""
    atual = pacote
    for info in caminho_reles:  # R1, R2, R3 (ordem do caminho)
        endereco_rele = info["endereco"]
        chave = chaves[endereco_rele]
        # Um relé do caminho não conseguiu falar com o próximo salto
        if isinstance(atual, dict) and atual.get("tipo") == "ERROR":
            return atual
        if not isinstance(atual, dict) or atual.get("tipo") != "RESPOSTA":
            raise RuntimeError(f"resposta inesperada: {atual}")
        atual = decifrar(chave, atual["dados"])
    return atual


if __name__ == "__main__":
    menu()