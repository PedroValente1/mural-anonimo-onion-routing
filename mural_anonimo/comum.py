import json
import socket
import struct
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

LIMITE = 10 * 1024 * 1024  # 10 MB


def enviar(sock, mensagem):
    """Envia um dicionário como [4 bytes de tamanho][JSON]."""
    dados = json.dumps(mensagem).encode("utf-8")
    tamanho = struct.pack("!I", len(dados))
    sock.sendall(tamanho + dados)


def receber_bytes(sock, n):
    """Lê exatamente n bytes. Devolve None se a conexão fechar antes."""
    pedacos = []
    faltam = n
    while faltam > 0:
        pedaco = sock.recv(faltam)
        if not pedaco:
            return None
        pedacos.append(pedaco)
        faltam -= len(pedaco)
    return b"".join(pedacos)


def receber(sock):
    """Lê os 4 bytes de tamanho, depois o JSON. Devolve dict ou None.
    https://youtu.be/m3MIwa5AH9U?si=mEbETwHa0AqvmmVr"""
    cabecalho = receber_bytes(sock, 4)
    if cabecalho is None:
        return None
    tamanho = struct.unpack("!I", cabecalho)[0]
    if tamanho > LIMITE:
        raise ValueError(f"Mensagem grande demais: {tamanho} bytes")
    corpo = receber_bytes(sock, tamanho)
    if corpo is None:
        return None
    return json.loads(corpo.decode("utf-8"))


def pedir(endereco, mensagem, timeout=10):
    """Abre conexão, envia, espera resposta, fecha. Devolve a resposta."""
    host, porta = endereco.split(":")
    porta = int(porta)
    with socket.create_connection((host, porta), timeout=timeout) as sock:
        enviar(sock, mensagem)
        return receber(sock)


def criar_servidor(host, porta):
    """Cria, configura e põe um socket TCP em modo de escuta."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, porta))
    servidor.listen()
    return servidor


def nova_chave():
    """Gera uma chave Fernet nova (bytes)."""
    return Fernet.generate_key()


def cifrar(chave, objeto):
    """Transforma um dicionário em JSON, cifra com a chave e devolve str."""
    texto = json.dumps(objeto).encode("utf-8")
    token = Fernet(chave).encrypt(texto)
    return token.decode("utf-8")


def decifrar(chave, texto):
    """Recebe uma string cifrada, decifra e devolve o dicionário."""
    token = texto.encode("utf-8")
    texto_decifrado = Fernet(chave).decrypt(token)
    return json.loads(texto_decifrado.decode("utf-8"))


def gerar_chaves():
    """Gera um par RSA. Devolve (privada, pem_publica_str)."""
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = privada.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return privada, pem


def cifrar_rsa(pem_publica, dados_bytes):
    """Cifra bytes com RSA-OAEP. Devolve hex str (para caber em JSON)."""
    publica = serialization.load_pem_public_key(pem_publica.encode())
    oaep = padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )
    cifrado = publica.encrypt(dados_bytes, oaep)
    return cifrado.hex()


def decifrar_rsa(privada, hex_str):
    """Decifra hex str com RSA-OAEP. Devolve bytes."""
    oaep = padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )
    cifrado = bytes.fromhex(hex_str)
    return privada.decrypt(cifrado, oaep)