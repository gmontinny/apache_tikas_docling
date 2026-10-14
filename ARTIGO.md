# Apache Tika vs Docling: Extração de Documentos em Pipelines de Dados no GCP

**Por:** Engenharia de Dados  
**Instituição:** Setor de Inteligência — Controladoria Geral do Estado de Mato Grosso (CGE-MT)  
**Finalidade:** Estudo de solução para definição da melhor abordagem de extração de documentos a ser implementada no Setor de Inteligência da CGE-MT  
**Ambiente:** Google Cloud Platform (GCP) com Apache Spark e Apache Airflow  
**Contexto:** Pipelines de ingestão em Data Lake para grandes volumes e ambientes vetoriais

---

## 1. Introdução

A Controladoria Geral do Estado de Mato Grosso (CGE-MT), por meio do seu Setor de Inteligência, tem como missão transformar grandes volumes de documentos institucionais em informação estruturada e acionável — contratos, relatórios de auditoria, prestações de contas, notas fiscais, pareceres técnicos e demais documentos do ciclo de controle interno do Estado.

Para viabilizar essa transformação em escala, é necessário definir a melhor abordagem tecnológica para extração de conteúdo de documentos não estruturados. Este estudo foi conduzido para embasar essa decisão, comparando duas tecnologias — **Apache Tika** e **Docling** — em um cenário real de Data Lake no GCP, orquestrado com Apache Airflow e processado com Apache Spark.

A escolha da ferramenta de extração impacta diretamente três dimensões críticas para o Setor de Inteligência:

- **Qualidade do dado** — o texto extraído representa fielmente o conteúdo original do documento público?
- **Custo operacional** — o pipeline escala sem comprometer o orçamento de TI do Estado?
- **Utilidade downstream** — o texto extraído serve bem para vetorização, RAG e assistentes de inteligência artificial?

Este artigo cobre tanto pipelines de alto volume quanto ambientes de inteligência artificial com vetorização, apresentando uma arquitetura de referência aplicável ao contexto da CGE-MT.

---

## 2. As Tecnologias

### 2.1 Apache Tika

O Apache Tika é um toolkit open source da Apache Software Foundation, com mais de 15 anos de maturidade. Sua proposta é simples e poderosa: detectar e extrair conteúdo de qualquer tipo de arquivo através de uma API unificada.

**Como funciona:**
- Recebe o arquivo via API REST (`PUT /tika`)
- Detecta automaticamente o formato (MIME type)
- Delega para o parser específico (PDFBox para PDF, POI para Office, Tesseract para OCR)
- Retorna texto plano ou metadados JSON

**Características técnicas:**
- Suporta +1.400 formatos de arquivo
- Servidor REST stateless — escala horizontalmente
- Imagem Docker oficial: `apache/tika:latest-full` (inclui Tesseract OCR)
- Consumo de memória: ~256MB por instância
- Latência: milissegundos para PDFs com texto nativo

### 2.2 Docling

O Docling é um projeto open source da IBM Research, lançado em 2024. Sua proposta é diferente: não apenas extrair texto, mas **compreender a estrutura semântica** do documento usando modelos de inteligência artificial.

**Como funciona:**
- Carrega o PDF e aplica modelos de layout detection (DocLayNet)
- Identifica regiões: título, parágrafo, tabela, figura, cabeçalho, rodapé
- Aplica OCR com EasyOCR quando necessário
- Exporta em Markdown estruturado ou JSON com hierarquia completa

**Características técnicas:**
- Foco em PDF, Word, PowerPoint, HTML
- Requer modelos de IA (~2-4GB de download no primeiro uso)
- Consumo de memória: 4-8GB por instância (CPU), reduz com GPU
- Latência: segundos a minutos por documento complexo
- Exporta Markdown com hierarquia preservada — ideal para chunking semântico

---

## 3. Resultado Experimental com PDFs Reais

Para embasar a comparação, foram processados três PDFs de boletins econômicos brasileiros usando ambas as ferramentas, com OCR habilitado (Tesseract para Tika, EasyOCR para Docling) e idioma configurado para português brasileiro.

### 3.1 Configurações aplicadas no Apache Tika

Para maximizar a extração, foram ativados três headers específicos do PDFBox:

```
X-Tika-PDFSortByPosition: true
X-Tika-PDFextractInlineImages: true
X-Tika-PDFextractAnnotationText: true
```

Além de pós-processamento para remoção de ruído (linhas em branco excessivas, espaços duplos).

### 3.2 Configurações aplicadas no Docling

```python
PdfPipelineOptions(
    do_ocr=True,
    ocr_options=EasyOcrOptions(lang=["pt"])
)
```

### 3.3 Resultados

| PDF | Tika (chars) | Docling (chars) | Diferença | Perfil do documento |
|---|---|---|---|---|
| Boletim ABRAINC 2tri25 | 18.155 | 18.033 | Empate | Texto nativo, layout simples |
| FipeZap Ago/2026 | 73.651 | 90.529 | **+23% Docling** | Tabelas de preço por cidade |
| IPOP Dez/2025 | 11.861 | 18.201 | **+53% Docling** | Tabelas densas de índices |

**Análise:** Em documentos com texto nativo e layout simples, ambas as ferramentas performam de forma equivalente. A diferença se torna expressiva em documentos com tabelas de dados — exatamente o perfil mais comum em ambientes financeiros, jurídicos e técnicos.

O gap não é de configuração — é estrutural. O Tika achata o conteúdo em texto plano; o Docling entende que aquela região da página é uma tabela e a preserva como tal.

---

## 4. Arquitetura no GCP com Apache Spark e Airflow

### 4.1 Visão Geral

```
                    ┌──────────────────────────────────────────┐
                    │           Google Cloud Storage           │
                    │         (Landing Zone — raw files)       │
                    └─────────────────┬────────────────────────┘
                                      │ Cloud Storage trigger
                                      ▼
                    ┌──────────────────────────────────────────┐
                    │         Cloud Pub/Sub                    │
                    │    (fila de eventos por arquivo)         │
                    └─────────────────┬────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────────────┐
                    │         Apache Airflow (Cloud Composer)  │
                    │                                          │
                    │  DAG: pdf_extraction_pipeline            │
                    │                                          │
                    │  1. classify_document                    │
                    │  2. branch: tika_extract / docling_extract│
                    │  3. save_to_gcs_curated                  │
                    │  4. trigger_spark_job                    │
                    └─────────────────┬────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
          ┌───────────────────────┐   ┌───────────────────────┐
          │  Tika Server          │   │  Docling Worker       │
          │  (Cloud Run / GKE)    │   │  (GKE + GPU node pool)│
          │  stateless, auto-scale│   │  batch processing     │
          └───────────┬───────────┘   └───────────┬───────────┘
                      │                           │
                      └───────────┬───────────────┘
                                  ▼
                    ┌──────────────────────────────────────────┐
                    │     GCS Curated Layer                    │
                    │  texto extraído + metadados JSON         │
                    └─────────────────┬────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────────────┐
                    │     Apache Spark (Dataproc)              │
                    │                                          │
                    │  - limpeza e normalização do texto       │
                    │  - chunking semântico                    │
                    │  - geração de embeddings em batch        │
                    │  - gravação no BigQuery e Vertex AI      │
                    └─────────────────┬────────────────────────┘
                                      │
                             ┌────────┴────────┐
                             ▼                 ▼
                       BigQuery            Vertex AI
                       (metadados,         Vector Search
                        analytics)         (embeddings RAG)
```

### 4.2 DAG do Airflow

A DAG central do pipeline usa `BranchPythonOperator` para rotear cada arquivo para o extrator correto com base em uma classificação prévia do documento.

```python
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.google.cloud.operators.dataproc import DataprocSubmitJobOperator
from datetime import datetime

def classify_document(**context):
    filename = context["dag_run"].conf.get("filename", "")
    # PDFs com texto nativo detectado via pymupdf (rápido, sem IA)
    # retorna "tika_extract" ou "docling_extract"
    return "tika_extract" if is_native_pdf(filename) else "docling_extract"

with DAG("pdf_extraction_pipeline", start_date=datetime(2024, 1, 1), schedule=None) as dag:

    classify = BranchPythonOperator(
        task_id="classify_document",
        python_callable=classify_document,
    )

    tika_task = PythonOperator(
        task_id="tika_extract",
        python_callable=run_tika_extraction,
    )

    docling_task = PythonOperator(
        task_id="docling_extract",
        python_callable=run_docling_extraction,
    )

    spark_job = DataprocSubmitJobOperator(
        task_id="spark_chunking_embedding",
        job={...},
        trigger_rule="none_failed_min_one_success",
    )

    classify >> [tika_task, docling_task] >> spark_job
```

### 4.3 Job Spark no Dataproc

O Spark entra após a extração para processar em larga escala: limpeza, chunking e geração de embeddings em batch.

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import ArrayType, StringType

spark = SparkSession.builder.appName("pdf_chunking").getOrCreate()

df = spark.read.json("gs://bucket/curated/*.json")

@udf(returnType=ArrayType(StringType()))
def chunk_text(text, extractor):
    if extractor == "docling":
        # chunk por seção markdown (##, ###)
        return chunk_by_section(text)
    else:
        # chunk por tamanho fixo com overlap
        return chunk_by_size(text, size=512, overlap=64)

df = df.withColumn("chunks", chunk_text(col("content"), col("extractor")))

# explode chunks para uma linha por chunk
df_chunks = df.select("filename", "extractor", explode("chunks").alias("chunk"))

# grava no BigQuery para indexação
df_chunks.write.format("bigquery").option("table", "dataset.chunks").save()
```

---

## 5. Requisitos para Grandes Volumes

### 5.1 Infraestrutura recomendada no GCP

| Componente | Serviço GCP | Configuração |
|---|---|---|
| Tika Server | Cloud Run | min=0, max=50, 1vCPU/512MB por instância |
| Docling Worker | GKE + GPU node pool | n1-standard-8 + T4 GPU, HPA por fila |
| Orquestração | Cloud Composer 2 | Ambiente pequeno, DAGs event-driven |
| Processamento | Dataproc Serverless | Spark sem cluster fixo, paga por job |
| Armazenamento raw | GCS Standard | Lifecycle policy para Nearline após 30 dias |
| Armazenamento curado | GCS + BigQuery | Particionado por data e tipo de extrator |
| Vetores | Vertex AI Vector Search | Index atualizado incrementalmente |

### 5.2 Estratégia de escala por volume

| Volume diário | Estratégia | Custo estimado GCP |
|---|---|---|
| < 1k documentos | Docling para tudo | Baixo — GKE spot instances |
| 1k – 50k documentos | Roteador: 80% Tika, 20% Docling | Médio — Cloud Run + GKE híbrido |
| > 50k documentos | Tika para tudo + chunker robusto | Alto volume, baixo custo unitário |
| Crítico (jurídico/financeiro) | Docling sempre | Qualidade acima de custo |

### 5.3 Otimizações para alto volume com Tika

- **Cloud Run com concorrência alta** — o Tika é stateless, suporta 80+ requisições simultâneas por instância
- **Pub/Sub como buffer** — desacopla a ingestão do processamento, evita perda de eventos em picos
- **Dataproc Serverless** — processa os textos extraídos em Spark sem manter cluster ocioso
- **Particionamento no GCS** — `gs://bucket/curated/year=2025/month=10/extractor=tika/`

---

## 6. Requisitos para Ambientes Vetoriais (RAG / LLMs)

### 6.1 Por que a qualidade do texto importa para embeddings

Um modelo de embedding transforma texto em um vetor numérico de alta dimensão. A qualidade desse vetor depende diretamente da qualidade do texto de entrada.

Quando o Tika extrai uma tabela de preços por cidade e o resultado é:

```
São Paulo R$ 12.500 Rio de Janeiro R$ 11.200 Curitiba R$ 8.900
Belo Horizonte R$ 9.100 Porto Alegre R$ 10.300
```

O embedding gerado representa uma sequência de palavras sem contexto. O modelo não sabe que isso é uma tabela, que os valores são preços, que cada par cidade-valor é uma entidade.

Quando o Docling extrai a mesma tabela:

```markdown
| Cidade | Preço médio (R$/m²) |
|---|---|
| São Paulo | 12.500 |
| Rio de Janeiro | 11.200 |
| Curitiba | 8.900 |
| Belo Horizonte | 9.100 |
| Porto Alegre | 10.300 |
```

O embedding gerado representa uma tabela estruturada com relações semânticas claras entre cidades e preços.

### 6.2 Estratégia de chunking por extrator

| Extrator | Estratégia de chunking | Ferramenta |
|---|---|---|
| Tika | Tamanho fixo (512 tokens) com overlap (64 tokens) | LangChain `RecursiveCharacterTextSplitter` |
| Docling | Por seção semântica (título → conteúdo) | LangChain `MarkdownHeaderTextSplitter` |

O chunking por seção do Docling é superior porque cada chunk carrega contexto completo: o título da seção + o conteúdo relacionado. Isso melhora drasticamente a precisão do retrieval em sistemas RAG.

### 6.3 Pipeline vetorial no GCP

```
  Texto extraído (GCS)
         │
         ▼
  Spark (Dataproc)
  ├── chunk_by_section()   ← Docling output
  └── chunk_by_size()      ← Tika output
         │
         ▼
  Vertex AI Embeddings API
  (text-embedding-004 / multilingual)
         │
         ▼
  Vertex AI Vector Search
  (índice ANN — busca aproximada)
         │
         ▼
  RAG Application
  (Vertex AI Agent Builder / LangChain)
```

### 6.4 Modelo de embedding recomendado para português

| Modelo | Provedor | Dimensões | Suporte PT-BR | Recomendado para |
|---|---|---|---|---|
| text-embedding-004 | Google Vertex AI | 768 | ✅ Nativo | Integração GCP nativa |
| text-multilingual-embedding-002 | Google Vertex AI | 768 | ✅ Nativo | Documentos multilíngues |
| BGE-M3 | BAAI (open source) | 1024 | ✅ Forte | Self-hosted no GKE |
| text-embedding-3-large | OpenAI | 3072 | ✅ Bom | Alta precisão, custo maior |

---

## 7. Comparativo Final

| Dimensão | Apache Tika | Docling |
|---|---|---|
| Velocidade | ⚡ Milissegundos | 🐢 Segundos a minutos |
| Formatos suportados | +1.400 | ~10 (foco em PDF/Office) |
| Qualidade em PDF simples | ✅ Boa | ✅ Boa |
| Qualidade em tabelas | ❌ Perde estrutura | ✅ Preserva estrutura |
| Qualidade em PDF escaneado | ⚠️ Básica (Tesseract) | ✅ Superior (IA + EasyOCR) |
| Consumo de recursos | 🟢 Baixo (256MB) | 🔴 Alto (4-8GB) |
| Escala horizontal | ✅ Trivial (stateless) | ⚠️ Complexo (GPU, modelos) |
| Qualidade do embedding gerado | ⚠️ Degradada pelo ruído | ✅ Alta fidelidade |
| Chunking semântico | ❌ Requer pós-processamento | ✅ Natural por seção |
| Custo em grande volume | 🟢 Muito baixo | 🔴 Alto (GPU) |
| Maturidade | ✅ 15+ anos | ⚠️ Projeto novo (2024) |
| Integração com Spark | ✅ tika-spark nativo | ⚠️ Via API REST/batch |

---

## 8. Conclusão

Este estudo foi conduzido para subsidiar a decisão do Setor de Inteligência da Controladoria Geral do Estado de Mato Grosso (CGE-MT) sobre a melhor abordagem de extração de documentos para seu Data Lake institucional.

Não existe uma resposta única para "qual é melhor". A escolha depende do perfil do documento e do caso de uso:

**Use Apache Tika quando:**
- O volume é alto (> 10k documentos/dia) e o custo é uma restrição
- Os documentos são heterogêneos (PDF, Excel, HTML, Word, imagens)
- A extração de texto plano é suficiente para o caso de uso
- A integração com Spark/Hadoop é prioritária
- O pipeline precisa de latência baixa e escala horizontal simples

**Use Docling quando:**
- A qualidade semântica do texto é crítica (RAG, LLMs, busca semântica)
- Os documentos têm tabelas, gráficos ou layouts complexos
- O domínio é financeiro, jurídico ou técnico — onde perder uma tabela é inaceitável
- O chunking inteligente por seção é necessário para melhorar o retrieval

**Recomendação para a CGE-MT:**

O perfil documental da Controladoria — contratos, relatórios de auditoria, prestações de contas, notas fiscais, pareceres técnicos — é predominantemente composto por documentos com tabelas de dados, valores monetários, índices e estruturas hierárquicas. Esse é exatamente o cenário onde o Docling demonstrou superar o Tika em até 53% na quantidade de conteúdo extraído, além de preservar a estrutura semântica das tabelas.

A arquitetura recomendada para o Setor de Inteligência da CGE-MT é o **roteador inteligente híbrido**:

1. Um classificador leve (Cloud Function no GCP) analisa o arquivo antes da extração
2. Documentos simples com texto nativo → **Tika no Cloud Run** (rápido e barato)
3. Documentos com tabelas, escaneados ou layouts complexos → **Docling no GKE com GPU**
4. O Spark no Dataproc processa ambos os outputs com estratégias de chunking diferenciadas
5. Os embeddings são gerados em batch e indexados no Vertex AI Vector Search
6. Assistentes de inteligência artificial consomem os vetores via RAG para suporte à tomada de decisão no controle interno

Essa abordagem híbrida captura o melhor dos dois mundos: a escala e o custo do Tika para documentos simples, e a precisão semântica do Docling para os documentos complexos que são o core do trabalho de inteligência da CGE-MT.

Em ambientes onde a qualidade do RAG é crítica — como análise de contratos públicos, detecção de irregularidades em prestações de contas ou cruzamento de dados de auditorias — o investimento no Docling se paga na precisão das respostas geradas pelos LLMs. Embeddings ruins geram respostas ruins, independente de qual modelo de linguagem está na ponta.

---

## 9. Referências

- Apache Tika — https://tika.apache.org/
- Apache Tika Docker — https://hub.docker.com/r/apache/tika
- Docling (IBM Research) — https://github.com/DS4SD/docling
- Docling Paper — https://arxiv.org/abs/2408.09869
- DocLayNet Dataset — https://arxiv.org/abs/2206.01062
- Apache Airflow — https://airflow.apache.org/
- Apache Spark — https://spark.apache.org/
- Google Cloud Composer — https://cloud.google.com/composer
- Google Dataproc Serverless — https://cloud.google.com/dataproc-serverless
- Vertex AI Vector Search — https://cloud.google.com/vertex-ai/docs/vector-search/overview
- Vertex AI Embeddings — https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings
- LangChain Text Splitters — https://python.langchain.com/docs/modules/data_connection/document_transformers/
- EasyOCR — https://github.com/JaidedAI/EasyOCR
- BGE-M3 Embedding Model — https://huggingface.co/BAAI/bge-m3
- PDFBox (usado pelo Tika) — https://pdfbox.apache.org/
