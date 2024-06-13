# 证书和颁发证书过程

### 先看几个概念

- **x509**：公钥证书的格式标准，规定了证书可以包含什么信息，并说明了记录信息的方法。
- **证书文件的两种格式**：
  - **pem和der**：两种（包括公私钥、证书签名请求、证书等内容的）格式，前者是文本形式，Linux常用，后者是二进制形式，Windows常用，仅仅是格式，不表明内容，如果作为后缀就像HTML起的效果一样。有时候用pem做公钥的后缀。
- **crt和cer**：常见的两种证书后缀名，前者大多数情况为pem格式，后者大多数情况为der格式。
- **csr**：证书签名请求，包含了公钥、用户名等信息。证书申请者只要把CSR文件提交给证书颁发机构后，证书颁发机构使用其根证书私钥签名就生成了证书公钥文件，也就是颁发给用户的证书。
- **key**：常见的密钥后缀名。

OpenSSL是一个开源软件库包，囊括了主要的密码算法、常用的密钥和证书封装管理功能以及SSL协议，并提供了丰富的应用程序供测试或其它目的使用。

### 使用OpenSSL生成和操作密钥和证书

```shell
# 以下命令为OpenSSL 1.1.1r 版本下的命令，不同版本下会有一些差别

# 1.生成一个RSA算法的密钥对
openssl genpkey -algorithm RSA -out rsa_private.key

# 2.通过命令将公钥导出到文件
openssl rsa -pubout -in rsa_private.key -out rsa_pub.key

# 生成一个测试文件：
echo "this is a test" > text

# 3.采用公钥对文件进行加密
openssl rsautl -encrypt -in text -inkey rsa_pub.key -pubin -out text.en

# 4.采用私钥解密文件
openssl rsautl -decrypt -in text.en -inkey rsa_private.key

# 5.用私钥对文件进行加密（签名）
openssl rsautl -sign -in text -inkey rsa_private.key -out text.en

# 6.用公钥对文件进行解密（校验）
openssl rsautl -verify -in text.en -inkey rsa_pub.key -pubin
```

# 证书和CA
公钥是公开分发的，那当你拿到一个公司（个人）的公钥之后，怎么确定这个公钥就是那个公司（个人）的？是否可能是被人篡改之后的公钥？而且公钥上没有任何的附加信息，标记当前公钥的所属的实体，相关信息等。

为了解决这个问题，人们引入了如下两个概念：

1）证书：公钥加上额外的其他信息（比如所属的实体，采用的加密解密算法等）= 证书。证书文件的扩展名一般为crt。

  ```shell
  # 查看证书：
  openssl x509 -noout -text -in /etc/pki/tls/certs/ca-bundle.crt
  ```

  2）CA：证书认证中心；拿到一个证书之后，得先去找CA验证下，看这个证书是否是一个“真”的证书，而不是一个篡改后的证书。如果确认证书没有问题，那么从证书中拿到公钥之后，就可以与对方进行安全的通信了，基于非对称加密机制。CA自身的分发及安全保证，一般是通过一些权威的渠道进行的，比如操作系统会内置一些官方的CA、浏览器也会内置一些CA；

```shell
# 采用CA校验一个证书（根ca证书可以用来验证子证书）
openssl verify -CAfile ca.cert tls.cert
```

# 创建自签名证书和证书颁发机构

我想给自己，给公司、给我的某个服务器申请一个证书，该怎么办？？？密钥对可以在自己的本地通过相关的工具（如openssl、ssh_keygen）产生，那公钥怎么包装成一个证书，并且在CA那边“注册”一下呢，不然，别人拿到你的证书之后，去CA那边验证不过，会认为是一个不可信证书？ 解决办法是将自己作为CA权威机构。

```shell
1) 生成一个密钥对
openssl ecparam -genkey -name SM2 -out root.key (国密sm2)
# openssl genpkey -algorithm rsa -out root.key (rsa)

2) 基于密钥生成一个CSR（证书签名请求）

openssl req -new -key root.key -out root.csr -subj "/C=CN/ST=HUB/L=WH/O=TRX/OU=LS/CN=TEST"

3) 查看下csr文件
openssl req -noout -text -in root.csr

4）将该CSR文件发给CA“注册一下”，当然了这个过程是收费的，要钱的，
这里，我们把自己当作一个CA权威机构，自己给自己注册一下，我们就成了一个自封的CA根证书，当然了，
产生的证书是没人认可的，但我们基于这个根证书生成的子证书，可以被我们认可，我们也可以为子证书提供验证
openssl x509 -req -days 36500 -sha1 -extensions v3_ca -signkey root.key -in root.csr -out root.crt

5) 创建二级证书密钥对
openssl ecparam -genkey -name SM2 -out sub.key (国密sm2)
# openssl genrsa -out sub.key 2048 (rsa)

6 ) 创建二级证书的证书申请文件（server.csr）
openssl req -new -key sub.key -out sub.csr -subj "/C=CN/ST=HUB/L=WH/O=TRX/OU=LS/CN=sss"

7) 使用根CA证书创建二级证书
openssl x509 -req -days 3650 -sha1 -extensions v3_req -CA root.crt -CAkey root.key -CAserial root.srl -CAcreateserial -in sub.csr -out sub.crt

8）使用根证书验证二级证书
openssl verify -CAfile root.crt sub.crt

9)查看颁发的新证书
openssl x509 -in sub.crt -noout -text (查看pem格式)
openssl x509 -in sub1.cer -inform der -noout -text (查看der格式)

10)Pem与der相互转换
Crt文件一般为pem格式，可以通过cat命令看到内容，cer文件一般为der二进制格式
openssl x509 -in sub.crt -outform der -out sub1.cer （pem转der）
openssl x509 -inform DER -outform PEM -text -in sub1.cer -out sub1.crt（der转pem）

11）从证书中提取出公钥
openssl x509 -in sub1.crt -pubkey -noout  (查看pem格式)
openssl x509 -in sub1.cer -inform der -pubkey -noout  (查看der格式)
```

# 创建中间证书颁发机构
在生产环境中，通常会使用中间证书颁发机构（Intermediate CA）来分发证书。这提供了更高的安全性，因为根证书的私钥可以离线存储，并且通过中间证书来颁发具体的服务器或客户端证书。

步骤如下：
### 1.生成中间CA的密钥和证书签名请求（CSR）
```shell
openssl genpkey -algorithm RSA -out intermediate.key
openssl req -new -key intermediate.key -out intermediate.csr -subj "/C=CN/ST=HUB/L=WH/O=TRX/OU=IT/CN=Intermediate CA"
```

### 2.使用根CA签署中间CA的证书
```shell
openssl x509 -req -in intermediate.csr -CA root.crt -CAkey root.key -CAcreateserial -out intermediate.crt -days 3650 -sha256 -extensions v3_ca
```

### 3.生成最终用户证书的密钥和证书签名请求（CSR）
```shell
openssl genpkey -algorithm RSA -out user.key
openssl req -new -key user.key -out user.csr -subj "/C=CN/ST=HUB/L=WH/O=TRX/OU=IT/CN=user.example.com"
```

### 4.使用中间CA签署最终用户证书
```shell
openssl x509 -req -in user.csr -CA intermediate.crt -CAkey intermediate.key -CAcreateserial -out user.crt -days 365 -sha256
```

### 5.验证证书链
```shell
cat intermediate.crt root.crt > ca-chain.crt
openssl verify -CAfile ca-chain.crt user.crt
```
这样，通过中间证书颁发机构，我们可以实现更灵活和安全的证书管理体系。这种方法可以减少根证书私钥暴露的风险，并且在需要撤销中间CA时不需要更改根CA。