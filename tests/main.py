from ownca import CertificateAuthority
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509

CA_STORAGE = "./CA"
ICA_STORAGE = "./ICA"
CA_COMMON_NAME = "topsec.org"
ICA_COMMON_NAME = "ica.topsec.org"
CA_DNS_NAMES = ["www.topsec.org", "ca.topsec.org"]


def save_certificate(cert, path):
    with open(path, "w") as cert_file:
        cert_file.write(cert.cert_bytes.decode())
        cert_file.close()


def save_chain(certs, path):
    with open(path, "w") as chain_file:
        for cert in certs:
            chain_file.write(cert.cert_bytes.decode())
        chain_file.close()


def load_certificate(path):
    with open(path, "rb") as cert_file:
        cert_data = cert_file.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        cert_file.close()
    return cert


if __name__ == '__main__':
    # 创建根证书颁发机构
    ca = CertificateAuthority(
        ca_storage=CA_STORAGE,
        common_name=CA_COMMON_NAME,
        dns_names=CA_DNS_NAMES,
    )

    # 创建中间证书颁发机构
    ica = CertificateAuthority(
        common_name=ICA_COMMON_NAME,
        ca_storage=ICA_STORAGE,
        dns_names=CA_DNS_NAMES,
        intermediate=True,
    )

    # # 根CA签署中间CA，中间CA拥有签名权限
    # ica_certificate = ca.sign_csr(ica.csr, ica.public_key, key_cert_sign=True, crl_sign=True)
    # save_certificate(ica_certificate, f"{ICA_STORAGE}/ca.crt")
    #
    # # 从文件加载中间证书颁发机构
    # ica = CertificateAuthority(
    #     common_name=ICA_COMMON_NAME,
    #     ca_storage=ICA_STORAGE,
    #     dns_names=CA_DNS_NAMES,
    #     intermediate=True,
    # )
    #
    # # 保存证书链
    # save_chain([ca, ica], f"{ICA_STORAGE}/chain.crt")
    #
    # # 使用中间CA颁发证书
    # # 如果服务器使用 IP 地址进行访问，并且需要这些 IP 地址被客户端验证，则需要将 IP 地址作为 Subject Alternative Name (IP SANs)。
    # # 否则，将DNS 名称作为dns SANs 即可了。
    server = ica.issue_certificate('10.28.134.2', ip_addresses=['10.28.134.2'])
    client = ica.issue_certificate('127.0.0.1')

    # 验证证书
    print("#######################")
    ca.public_key.verify(
        ica.cert.signature,
        ica.cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        ica.cert.signature_hash_algorithm,
    )
    print("中间CA证书由根CA签名验证成功")

    ica.public_key.verify(
        server.cert.signature,
        server.cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        server.cert.signature_hash_algorithm,
    )
    print("服务器证书由中间CA签名验证成功")

    ica.public_key.verify(
        client.cert.signature,
        client.cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        client.cert.signature_hash_algorithm,
    )
    print("客户端证书由中间CA签名验证成功")

    # 验证证书链
    chain_cert = load_certificate(f"{ICA_STORAGE}/chain.crt")
    ca.public_key.verify(
        chain_cert.signature,
        chain_cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        chain_cert.signature_hash_algorithm,
    )
    print("证书链验证成功")
    ica.revoke_certificate('127.0.0.1')
    # 验证由中间CA签署的证书
    for cert in [server, client]:
        print(cert.revoked)  # 需重新加载server，client
        ica.public_key.verify(
            cert.cert.signature,
            cert.cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.cert.signature_hash_algorithm,
        )
        print(f"{cert.cert.subject}证书由中间CA验证成功")
