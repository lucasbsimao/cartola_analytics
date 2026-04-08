# RUN

Para rodar, é necessário o seguinte comando:

```
make run
```

Ou alternativamente:

```
uv run python main.py
```

## Setup

Para instalar as dependências:

```
make sync
```

Ou:

```
uv sync
```

## Makefile Targets

- `make run` - Executa o programa principal
- `make sync` - Instala/sincroniza as dependências
- `make clean` - Remove arquivos de cache e venv

# DOCS

COMUNIDADE DEV CARTOLA

https://gitter.im/cartrolandofc/dev?at=5d7f945836461106bb2aa3e6

Estado mercado atual

https://api.cartola.globo.com/atletas/mercado

Ids dos clubes

https://api.cartola.globo.com/clubes

Pontuação dos atletas com scouts por rodada

https://api.cartola.globo.com/atletas/pontuados/1

Verificar partidas das rodadas

https://api.cartola.globo.com/partidas/1


https://stackoverflow.com/a/26887820

Possível autenticação

captcha: "",
payload: {
        email: "email@gmail.com",
        password: "pass",
        serviceId: 4728

}
