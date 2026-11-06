import sys
import threading
from comum import (
    criar_servidor, receber, enviar, pedir,
    gerar_chaves, cifrar_rsa, decifrar_rsa,
    cifrar, decifrar,
)


DIRETORIO = "127.0.0.1:9000"


def atender(conexao, endereco, nome, privada):
    try:
        pacote = receber(conexao)
        if pacote is None:
            return

        if pacote.get("tipo") != "CEBOLA":
            enviar(conexao, {"tipo": "ERROR", "motivo": "esperava CEBOLA"})
            return

        # 1. Decifra a chave Fernet com a privada RSA
        chave_fernet = decifrar_rsa(privada, pacote["chave"])

        # 2. Decifra os dados com a chave Fernet
        corpo = decifrar(chave_fernet, pacote["dados"])
        proximo = corpo["proximo"]
        conteudo = corpo["conteudo"]

        print(f"[{nome}] recebi de {endereco}, repassando para {proximo}")

        try:
            resposta = pedir(proximo, conteudo)
        except OSError as e:
            print(f"[{nome}] falha ao contactar {proximo}: {e}")
            enviar(conexao, {"tipo": "ERROR", "motivo": f"proximo fora do ar"})
            return

        # 3. Cifra a resposta com a mesma chave Fernet
        resposta_cifrada = cifrar(chave_fernet, resposta)
        enviar(conexao, {"tipo": "RESPOSTA", "dados": resposta_cifrada})
    finally:
        conexao.close()


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 rele.py <nome> <porta>")
        sys.exit(1)

    nome = sys.argv[1]
    porta = int(sys.argv[2])
    endereco = f"127.0.0.1:{porta}"

    # Gera par RSA
    privada, pem_publica = gerar_chaves()
    print(f"[{nome}] chaves geradas")

    # Registra no diretório
    try:
        resposta = pedir(DIRETORIO, {
            "tipo": "REGISTRAR",
            "nome": nome,
            "endereco": endereco,
            "chave_publica": pem_publica,
        })
        if resposta is None or resposta.get("tipo") != "OK":
            print(f"[{nome}] erro ao registrar: {resposta}")
            sys.exit(1)
        print(f"[{nome}] registrado no diretório")
    except OSError as e:
        print(f"[{nome}] não consegui falar com o diretório: {e}")
        print("O diretório está rodando?")
        sys.exit(1)

    servidor = criar_servidor("127.0.0.1", porta)
    print(f"[{nome}] escutando em {endereco}")
    while True:
        conexao, end_cliente = servidor.accept()
        t = threading.Thread(
            target=atender,
            args=(conexao, end_cliente, nome, privada),
            daemon=True,
        )
        t.start()


if __name__ == "__main__":
    main()