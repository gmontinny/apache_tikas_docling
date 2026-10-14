# Apache Tika vs Docling — Extração de PDFs

Este projeto lê arquivos PDF da pasta `datas`, extrai o texto usando duas ferramentas diferentes (**Apache Tika** e **Docling**) e salva os resultados em um banco de dados para comparação.

---

## O que você precisa instalar antes

Antes de começar, instale os dois programas abaixo. Se já tiver, pode pular.

### 1. Python
👉 https://www.python.org/downloads/

> Durante a instalação, marque a opção **"Add Python to PATH"**

### 2. Docker Desktop
👉 https://www.docker.com/products/docker-desktop/

> Após instalar, abra o Docker Desktop e aguarde ele iniciar (ícone na barra de tarefas fica verde).

---

## Como instalar o projeto

1. Baixe ou clone este projeto no seu computador
2. Abra a pasta do projeto
3. Dê dois cliques no arquivo **`setup.bat`**

O script vai:
- ✅ Verificar se Python e Docker estão instalados
- ✅ Criar o arquivo de configuração `.env`
- ✅ Subir o banco de dados e o servidor Tika automaticamente
- ✅ Instalar todas as dependências Python

> ⚠️ Na primeira vez pode demorar alguns minutos pois irá baixar os modelos de inteligência artificial do Docling.

---

## Como executar

Após o setup, basta dar dois cliques no arquivo **`executar.bat`**.

Ou, pelo terminal:
```bash
python src/main.py
```

Os PDFs da pasta `datas` serão processados e o resultado salvo no banco de dados.

---

## Onde ver os resultados

Os resultados ficam salvos na tabela `pdf_extractions` do PostgreSQL. Para consultar:

```sql
SELECT filename, extractor, length(content) AS caracteres, extracted_at
FROM pdf_extractions
ORDER BY filename, extractor;
```

---

## Estrutura do projeto

```
.
├── datas/                   # Coloque seus PDFs aqui
├── src/
│   ├── db.py                # Conexão com o banco de dados
│   ├── extractor_tika.py    # Extração via Apache Tika
│   ├── extractor_docling.py # Extração via Docling
│   └── main.py              # Programa principal
├── .env                     # Suas configurações (criado pelo setup.bat)
├── .env.example             # Modelo de configurações
├── docker-compose.yml       # Banco de dados + Tika Server
├── requirements.txt         # Dependências Python
├── setup.bat                # ← Execute este primeiro!
└── executar.bat             # ← Execute este para rodar
```

---

## Configurações (arquivo `.env`)

Você não precisa alterar nada para rodar localmente. Mas se precisar, as opções são:

| Variável          | Padrão                | O que é                     |
|-------------------|-----------------------|-----------------------------|
| POSTGRES_HOST     | localhost             | Endereço do banco de dados  |
| POSTGRES_PORT     | 5432                  | Porta do banco de dados     |
| POSTGRES_DB       | app_db                | Nome do banco               |
| POSTGRES_USER     | postgres              | Usuário do banco            |
| POSTGRES_PASSWORD | postgres              | Senha do banco              |
| TIKA_SERVER_URL   | http://localhost:9998 | Endereço do servidor Tika   |
| DATA_DIR          | datas                 | Pasta com os PDFs           |

---

## Avisos comuns (não são erros)

**`torch.quint8 / qint8 / qint32 deprecated`**
→ Aviso interno do PyTorch gerado pelos modelos de IA do Docling. Não afeta o resultado, pode ignorar.

**`hf_xet package is not installed`**
→ O HuggingFace tem um protocolo mais rápido para download de modelos, mas é opcional. Para silenciar o aviso:
```bash
pip install huggingface_hub[hf_xet]
```

---

## Problemas comuns

**"Docker não encontrado"**
→ Abra o Docker Desktop e aguarde iniciar antes de rodar o `setup.bat`.

**"Erro ao instalar dependências"**
→ Tente rodar o `setup.bat` como Administrador (botão direito → Executar como administrador).

**A extração demorou muito**
→ Normal na primeira vez. O Docling baixa modelos de IA que ficam em cache para as próximas execuções.

---

## Comparativo: Apache Tika vs Docling

### Resultado real com os PDFs deste projeto

| PDF | Tika (chars) | Docling (chars) | Diferença | Observação |
|---|---|---|---|---|
| Boletim ABRAINC 2tri25 | 18.155 | 18.033 | Empate | PDF simples, texto nativo |
| FipeZap Ago/2026 | 73.651 | 90.529 | **+23% Docling** | Tabelas de preço por cidade |
| IPOP Dez/2025 | 11.861 | 18.201 | **+53% Docling** | Tabelas de índices de obras |

> As melhorias no Tika limparam o texto (menos ruído), mas não fecharam a diferença em conteúdo — o gap é estrutural. O Docling entende o layout do PDF; o Tika achata tudo em texto plano independente de configuração.

---

### Melhorias aplicadas no Apache Tika

Para reduzir a diferença em relação ao Docling, foram aplicadas 3 otimizações no extractor:

**1. `X-Tika-PDFSortByPosition: true`**
→ Instrui o PDFBox a respeitar a posição visual dos elementos na página. Sem isso, colunas lado a lado e células de tabela saem intercaladas e fora de ordem.

**2. `X-Tika-PDFextractInlineImages: true`**
→ Extrai texto embutido em imagens inline dentro do PDF, como labels de gráficos e legendas.

**3. `X-Tika-PDFextractAnnotationText: true`**
→ Captura texto de anotações e comentários do PDF que o Tika ignora por padrão.

**4. Pós-processamento do texto**
→ Remove linhas em branco excessivas, espaços duplos e espaços antes de quebra de linha gerados pelo achatamento de tabelas.

---

### Apache Tika

**Vantagens**
- Extremamente leve e rápido — ideal para alto volume de arquivos em pipelines de ingestão
- Suporta +1400 formatos (PDF, Word, Excel, HTML, imagens, áudio, vídeo...) — perfeito para data lakes com arquivos heterogêneos
- API REST stateless — escala horizontalmente sem esforço, basta subir mais containers
- Baixo consumo de memória e CPU — barato para rodar em larga escala
- Maduro e estável — mais de 15 anos de projeto Apache
- Integração nativa com ecossistema Hadoop/Spark via `tika-spark`

**Desvantagens**
- Extração "burra" — joga tudo como texto plano, sem entender estrutura semântica (tabelas viram texto bagunçado)
- OCR básico — depende do Tesseract puro, sem modelos de IA para layouts complexos
- Não distingue título, rodapé, tabela, parágrafo
- PDFs escaneados com layout complexo (duas colunas, tabelas aninhadas) geram resultados ruins mesmo com as otimizações

---

### Docling

**Vantagens**
- Entende estrutura semântica — identifica títulos, parágrafos, tabelas, listas, cabeçalhos, rodapés
- OCR com modelos de IA (EasyOCR + modelos IBM) — muito superior em PDFs escaneados e layouts complexos
- Exporta em Markdown/JSON estruturado — facilita uso downstream (RAG, LLMs, indexação semântica)
- Ideal para documentos financeiros, jurídicos e técnicos
- Preserva hierarquia do documento — útil para chunking inteligente em pipelines de IA

**Desvantagens**
- Pesado — consome muita RAM e CPU/GPU, caro para escalar horizontalmente
- Lento — processa um PDF complexo em segundos/minutos vs milissegundos do Tika
- Suporta poucos formatos — foco em PDF, Word, PowerPoint; longe dos 1400+ do Tika
- Modelos de IA precisam ser baixados (~GBs) — cold start problemático em auto-scaling
- Projeto relativamente novo — menos testado em produção de larga escala

---

## Arquitetura ideal em Data Lake com auto-processamento

A estratégia mais eficiente é usar um **roteador inteligente** que decide qual extrator usar com base no tipo e complexidade do arquivo — evitando pagar o custo computacional do Docling em arquivos simples.

```
                   ┌─────────────────────────────────────┐
                   │           S3 / Data Lake            │
                   │   (landing zone — arquivos brutos)  │
                   └──────────────┬──────────────────────┘
                                  │ evento de novo arquivo
                                  ▼
                   ┌─────────────────────────────────────┐
                   │         Roteador / Classifier       │
                   │  (Lambda ou Step Functions)         │
                   │                                     │
                   │  PDF simples / texto nativo?  ──────┼──► Tika (ECS Fargate)
                   │  PDF escaneado / complexo?    ──────┼──► Docling (ECS GPU)
                   │  Excel, HTML, Word, etc.?     ──────┼──► Tika (ECS Fargate)
                   └─────────────────────────────────────┘
                                  │
                                  ▼
                   ┌─────────────────────────────────────┐
                   │         Camada Curated (S3)         │
                   │   texto extraído + metadados JSON   │
                   └──────────────┬──────────────────────┘
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
               PostgreSQL / RDS      OpenSearch / S3
               (resultados)          (indexação semântica
                                      / RAG com LLMs)
```

| Cenário | Extrator recomendado | Motivo |
|---|---|---|
| PDF com texto nativo selecionável | **Tika** | Rápido e barato |
| PDF escaneado ou com tabelas complexas | **Docling** | Preciso e estruturado |
| Excel, HTML, CSV, Word | **Tika** | Único que suporta todos esses formatos |
| Pipeline de RAG / LLM | **Docling** | Exporta Markdown estruturado com hierarquia |
| Alto volume (milhares de arquivos/dia) | **Tika** | Escala horizontal sem custo de GPU |

---

## Vetorização em Data Lake

### Quem ganha na vetorização?

**Docling, sem dúvida.** Vetorização (embeddings para RAG, busca semântica, LLMs) depende diretamente da qualidade e estrutura do texto de entrada. Lixo entra, lixo sai no vetor.

| Critério | Tika | Docling |
|---|---|---|
| Qualidade do chunk | Texto plano, sem contexto | Markdown estruturado com hierarquia |
| Tabelas | Viram texto bagunçado | Preservadas como tabela |
| Títulos e seções | Perdidos | Identificados — permitem chunking por seção |
| Chunking inteligente | Impossível sem pós-processamento | Natural — corta por título/parágrafo/tabela |
| Ruído no vetor | Alto — rodapés, cabeçalhos, lixo misturado | Baixo — estrutura semântica limpa |
| Qualidade do embedding | Degradada pelo ruído | Alta fidelidade ao conteúdo original |

O problema do Tika não é só quantidade de texto — é que o vetor gerado a partir de texto plano bagunçado **representa mal o conteúdo**. Uma tabela de preços por cidade virada em texto intercalado gera um embedding que não representa nem a tabela nem o texto.

---

### Arquitetura para grandes volumes com vetorização

```
                    ┌─────────────────────────────────────┐
                    │         S3 Landing Zone             │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │      Classificador (Lambda)         │
                    │                                     │
                    │  PDF texto nativo? ─────────────────┼──► Tika (Fargate)
                    │  PDF complexo/escaneado? ───────────┼──► Docling (ECS GPU)
                    └─────────────────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │     Chunker Semântico               │
                    │  (LangChain / LlamaIndex)           │
                    │                                     │
                    │  Tika output ──► chunk por tamanho  │
                    │  Docling output ► chunk por seção   │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │     Modelo de Embedding             │
                    │  (Amazon Titan / OpenAI / BGE)      │
                    └──────────────┬──────────────────────┘
                                   │
                          ┌────────┴────────┐
                          ▼                 ▼
                    OpenSearch          PostgreSQL
                    (pgvector)          + RDS
                    busca semântica     metadados
```

---

### Estratégia por volume

| Volume | Estratégia | Custo |
|---|---|---|
| Baixo (< 1k docs/dia) | Docling para tudo | Aceitável |
| Médio (1k–50k docs/dia) | Roteador: Tika para simples, Docling para complexos | Otimizado |
| Alto (> 50k docs/dia) | Tika para tudo + pós-processamento + chunker robusto | Barato e escalável |
| Crítico (jurídico, financeiro) | Docling sempre, independente do volume | Qualidade acima de custo |

---

### Recomendação final

- **Qualidade máxima de RAG** → Docling, sempre. O embedding gerado a partir do Markdown estruturado é significativamente mais preciso.
- **Grande volume com custo controlado** → Roteador inteligente. 80% dos documentos em data lakes são PDFs simples — o Tika resolve bem e barato. Reserve o Docling para os 20% complexos.
- **Nunca vetorize direto do Tika sem chunker** → o texto plano sem estrutura gera embeddings ruins que degradam a qualidade do RAG inteiro.
