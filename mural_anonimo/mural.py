import threading
import hashlib
from comum import criar_servidor, receber, enviar

HOST = "127.0.0.1"
PORTA = 7000

TOPICOS_FIXOS = ["geral", "dúvidas", "off-topic"]


def hash_senha(senha):
    """Calcula SHA-256 de uma senha (string) e devolve hex."""
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def formatar_autor(apelido, hash_):
    """Se tem hash, mostra 'apelido!8chars'. Senão, só o apelido."""
    if hash_:
        return f"{apelido}!{hash_[:8]}"
    return apelido


posts = []
proximo_id = 1
trava = threading.Lock()


def tratar_pedido(pedido):
    """Recebe um dicionário e devolve o dicionário de resposta.
    Não usa sockets, então pode ser testado isoladamente."""

    tipo = pedido.get("tipo")

    if tipo == "TOPICOS":
        return {"tipo": "TOPICOS", "lista": TOPICOS_FIXOS}

    if tipo == "LISTAR":
        topico = pedido.get("topico")
        if topico not in TOPICOS_FIXOS:
            return {"tipo": "ERROR", "motivo": f"topico inexistente: {topico}"}
        with trava:
            lista = [
                {
                    "id": p["id"],
                    "titulo": p["titulo"],
                    "autor": formatar_autor(p["apelido"], p.get("hash")),
                    "respostas": len(p["respostas"]),
                }
                for p in posts
                if p["topico"] == topico
            ]
        return {"tipo": "POSTS", "posts": lista}
    
    if tipo == "LER":
        id_post = pedido.get("id")
        with trava:
            post = next((p for p in posts if p["id"] == id_post), None)
            if post is None:
                return {"tipo": "ERROR", "motivo": f"post inexistente: {id_post}"}
            respostas_formatadas = [
                {
                    "apelido": formatar_autor(r["apelido"], r.get("hash")),
                    "texto": r["texto"],
                }
                for r in post["respostas"]
            ]
            autor_formatado = formatar_autor(post["apelido"], post.get("hash"))
            titulo = post["titulo"]
            texto = post["texto"]
        return {
            "tipo": "POST",
            "autor": autor_formatado,
            "titulo": titulo,
            "texto": texto,
            "respostas": respostas_formatadas,
        }
    
    if tipo == "POSTAR":
        topico = pedido.get("topico")
        if topico not in TOPICOS_FIXOS:
            return {"tipo": "ERROR", "motivo": f"topico inexistente: {topico}"}
        senha = pedido.get("senha", "")
        hash_ = hash_senha(senha) if senha else None
        global proximo_id
        with trava:
            novo = {
                "id": proximo_id,
                "topico": topico,
                "titulo": pedido.get("titulo", ""),
                "texto": pedido.get("texto", ""),
                "apelido": pedido.get("apelido", "anônimo"),
                "hash": hash_,
                "respostas": [],
            }
            posts.append(novo)
            id_novo = proximo_id
            proximo_id += 1
        return {"tipo": "OK", "id": id_novo}
    
    if tipo == "RESPONDER":
        id_post = pedido.get("id")
        senha = pedido.get("senha", "")
        hash_ = hash_senha(senha) if senha else None
        with trava:
            post = next((p for p in posts if p["id"] == id_post), None)
            if post is None:
                return {"tipo": "ERROR", "motivo": f"post inexistente: {id_post}"}
            post["respostas"].append({
                "apelido": pedido.get("apelido", "anônimo"),
                "hash": hash_,
                "texto": pedido.get("texto", ""),
            })
        return {"tipo": "OK"}
    
    if tipo == "APAGAR":
        id_post = pedido.get("id")
        senha = pedido.get("senha", "")
        if not senha:
            return {"tipo": "ERROR", "motivo": "APAGAR exige senha"}
        with trava:
            post = next((p for p in posts if p["id"] == id_post), None)
            if post is None:
                return {"tipo": "ERROR", "motivo": f"post inexistente: {id_post}"}
            if not post.get("hash"):
                return {"tipo": "ERROR", "motivo": "post sem senha, não pode ser apagado"}
            if hash_senha(senha) != post["hash"]:
                return {"tipo": "ERROR", "motivo": "senha incorreta"}
            posts.remove(post)
        return {"tipo": "OK"}

def atender(conexao, endereco):
    """Atende UMA conexão. Uma conexão = um pedido."""
    try:
        pedido = receber(conexao)
        if pedido is None:
            return
        tipo = pedido.get("tipo", "?")
        print(f"[{endereco}] pedido: {tipo}")
        resposta = tratar_pedido(pedido)
        enviar(conexao, resposta)
    finally:
        conexao.close()


def main():
    servidor = criar_servidor(HOST, PORTA)
    print(f"Mural escutando em {HOST}:{PORTA}")
    while True:
        conexao, endereco = servidor.accept()
        t = threading.Thread(target=atender, args=(conexao, endereco), daemon=True)
        t.start()


if __name__ == "__main__":
    main()