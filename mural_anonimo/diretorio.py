import threading
from comum import criar_servidor, receber, enviar

HOST = "127.0.0.1"
PORTA = 9000

reles = {}   # nome -> {"endereco": ..., "chave_publica": ...}
trava = threading.Lock()


def tratar_pedido(pedido):
    tipo = pedido.get("tipo")

    if tipo == "REGISTRAR":
        nome = pedido.get("nome")
        endereco = pedido.get("endereco")
        chave = pedido.get("chave_publica")
        if not (nome and endereco and chave):
            return {"tipo": "ERROR", "motivo": "campos faltando"}
        with trava:
            reles[nome] = {"endereco": endereco, "chave_publica": chave}
        print(f"Registrado: {nome} em {endereco}")
        return {"tipo": "OK"}

    if tipo == "LISTAR_RELES":
        with trava:
            lista = [
                {"nome": n, "endereco": r["endereco"], "chave_publica": r["chave_publica"]}
                for n, r in reles.items()
            ]
        return {"tipo": "RELES", "lista": lista}

    return {"tipo": "ERROR", "motivo": f"tipo desconhecido: {tipo}"}


def atender(conexao, endereco):
    try:
        pedido = receber(conexao)
        if pedido is None:
            return
        print(f"[diretorio] {endereco} → {pedido.get('tipo')}")
        resposta = tratar_pedido(pedido)
        enviar(conexao, resposta)
    finally:
        conexao.close()


def main():
    servidor = criar_servidor(HOST, PORTA)
    print(f"Diretório escutando em {HOST}:{PORTA}")
    while True:
        conexao, endereco = servidor.accept()
        t = threading.Thread(target=atender, args=(conexao, endereco), daemon=True)
        t.start()


if __name__ == "__main__":
    main()