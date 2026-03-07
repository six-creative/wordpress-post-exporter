# WordPress Post Exporter

Ferramenta em Python para exportar **todos os posts publicados** de um site WordPress via API oficial (`wp-json/wp/v2`) com metadados completos.

## O que esta ferramenta exporta

Para cada post publicado, a exportação inclui:

- ID, status, tipo, slug, link e datas (`date`, `date_gmt`, `modified`, `modified_gmt`)
- Título, resumo e conteúdo nas versões:
  - `rendered`
  - `raw` (quando disponível via `context=edit`)
- Autor:
  - `author_id`
  - `author_name`
- Taxonomias:
  - categorias (IDs e nomes)
  - tags (IDs e nomes)
- Campos adicionais:
  - `featured_media`, `comment_status`, `ping_status`, `template`, `format`, `meta`
- `raw_post_json` com o payload completo retornado pela API (útil para conteúdo grande e campos customizados)

## Requisitos

- Python 3.10+
- Acesso à API REST do WordPress com credenciais válidas

## Instalação

1. (Opcional, recomendado) criar e ativar um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

## Formatos de saída

A ferramenta suporta:

- `csv`
- `sql` (dump SQL de uma base SQLite contendo a tabela `posts`)

## Autenticação suportada

Use **uma** das opções abaixo:

1. Bearer token
- `--token`

2. Application Password (WordPress)
- `--username`
- `--application-password`

## Uso

### Com Bearer token

```bash
python3 main.py \
  --base-url https://seusite.com \
  --token SEU_TOKEN \
  --format csv \
  --output posts.csv
```

### Com usuário + application password

```bash
python3 main.py \
  --base-url https://seusite.com \
  --username admin \
  --application-password "xxxx xxxx xxxx xxxx" \
  --format sql \
  --output posts.sql
```

## Parâmetros da CLI

- `--base-url` (obrigatório): URL base do WordPress. Ex.: `https://seusite.com`
- `--format`: `csv` ou `sql` (padrão: `csv`)
- `--output` (obrigatório): caminho do arquivo de saída
- `--token`: token Bearer
- `--username`: usuário WordPress
- `--application-password`: senha de aplicação do WordPress
- `--timeout`: timeout por chamada HTTP em segundos (padrão: `30`)

## Exemplo de execução

Saída esperada ao final:

```text
Exportação concluída. N posts salvos em: caminho/do/arquivo
```

## Estrutura do projeto

```text
.
├── main.py
├── requirements.txt
└── wp_exporter
    ├── __init__.py
    ├── client.py
    ├── config.py
    ├── exporters.py
    ├── service.py
    └── transformers.py
```

## Observações

- A exportação usa paginação (`per_page=100`) e percorre todas as páginas disponíveis.
- A API é chamada com `context=edit` para tentar obter campos `raw` quando o usuário tem permissão.
- Se o site tiver plugins/campos customizados, o `raw_post_json` preserva o conteúdo retornado pela API.

## Troubleshooting

1. Erro de autenticação (`401`/`403`)
- Verifique token/credenciais e permissões da conta.
- Confirme se a API REST está habilitada no site.

2. Campos `raw` vazios
- Pode ser limitação de permissão no usuário autenticado.
- Em alguns cenários, o WordPress retorna apenas `rendered`.

3. Timeout/rede
- Aumente `--timeout`.
- Verifique conectividade e bloqueios (WAF/firewall/proxy).
