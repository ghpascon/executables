# Dispatches no X-BRIDGE

Este documento explica como funcionam os dispatches, onde eles ficam no projeto, como criar pelo frontend (aba Dispatches ou rota /settings/dispatches), quais sao os 4 tipos suportados e como configurar da melhor forma.

## O que e um dispatch

Dispatch e uma regra de roteamento de evento. Sempre que o sistema recebe um evento (por exemplo `tag`, `reading` ou eventos customizados), ele pode encaminhar esse dado para um destino externo.

Exemplos de destino:

- Endpoint HTTP (webhook)
- Banco SQL
- Broker MQTT
- MongoDB

## Onde os dispatches ficam no projeto

- Pasta de configuracao ativa: `config/dispatchers/`

Cada dispatch é salvo como um arquivo JSON, por exemplo:

- `config/dispatchers/meu_dispatch.json`

## Estrutura geral de um dispatch

Todos os tipos usam uma base parecida:

- `dispatch_type`: tipo do dispatch (`post`, `sql`, `mqtt`, `mongodb`)
- `on_event`: nome do evento que deve disparar o envio
- `allow_batches`: habilita lote
- `batch_size`: quantidade maxima por lote
- `flush_interval_seconds`: tempo maximo antes de enviar o lote
- `retry_attempts`: tentativas em falha
- `retry_backoff_seconds`: intervalo entre tentativas
- `filters`: filtros para restringir o envio

Todo evento possui tres partes: `device` (dict com `name` e `serial_number`), `event_type` e `event_data`. O `serial_number` e `null` enquanto o leitor ainda nao o informou.

Placeholders suportados (templates):

- `{name}`: nome do device
- `{serial_number}`: numero de serie do device (`null` se desconhecido)
- `{device}`: dict completo do device (`{"name": ..., "serial_number": ...}`)
- `{device[chave]}`: campo especifico do device (ex.: `{device[serial_number]}`)
- `{event_type}`: tipo do evento
- `{data}`: payload bruto do evento
- `{data[chave]}`: campo especifico quando `data` é um objeto/dict (ex.: `{data[epc]}`)

Operadores de filtro suportados:

- `eq`
- `ne`
- `in`
- `not_in`
- `gt`
- `lt`
- `gte`
- `lte`
- `contains`

## Como adicionar pelo frontend

Voce pode abrir a tela de duas formas:

- Menu superior: `Settings` -> `Dispatches`
- URL direta: `/settings/dispatches`

Passo a passo:

1. Clique em `Create Dispatch`.
2. Informe o `Dispatch Name` (nome do arquivo/identificador).
3. Em `Select example...`, escolha um exemplo base para carregar um JSON pronto.
4. Ajuste o conteudo JSON no editor da janela.
5. Clique em salvar.

Comportamentos importantes:

- Em edicao, o nome do dispatch fica bloqueado (somente leitura).
- A lista mostra os dispatches existentes.
- Acoes disponiveis na lista: `Edit` e `Delete`.

## Como adicionar manualmente no config

1. Crie um arquivo JSON em `config/dispatchers/`.
2. Use um exemplo da pasta `examples/dispatchers/` como base.
3. Ajuste os campos obrigatorios do tipo escolhido.
4. Salve o arquivo.

Observacao:

- Se houver duvida sobre recarga em tempo real no ambiente atual, reinicie a aplicacao para garantir leitura do novo arquivo.

## Os 4 tipos de dispatch

### 1) Tipo `post` (HTTP)

Envia eventos para um endpoint HTTP.

Campos principais:

- `url`: URL de destino
- `headers`: cabecalhos HTTP
- `body`: payload enviado (aceita placeholders)

Quando usar:

- Integracao com APIs/webhooks
- Encaminhar eventos para outro servico

Boas praticas:

- Defina `Authorization` no header quando necessario.
- Use `filters` para reduzir ruido de evento.
- Comece com `retry_attempts: 3` e `retry_backoff_seconds: 0.25`.

Exemplo minimo:

```json
{
  "dispatch_type": "post",
  "url": "http://localhost:5001",
  "on_event": "tag",
  "allow_batches": true,
  "batch_size": 500,
  "flush_interval_seconds": 0.1,
  "retry_attempts": 3,
  "retry_backoff_seconds": 0.25,
  "filters": [],
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "device": "{name}",
    "device_serial_number": "{device[serial_number]}",
    "epc": "{data[epc]}"
  }
}
```

### 2) Tipo `sql`

Insere eventos em banco relacional via query parametrizada.

Campos principais:

- `connection_string`: string de conexao assincrona
- `query`: SQL com parametros nomeados (ex.: `:device`)
- `params`: mapeamento dos parametros para placeholders

Quando usar:

- Persistencia estruturada
- Relatorios e consultas SQL

Boas praticas:

- Use query parametrizada, nunca concatenacao de string.
- Indexe colunas de consulta frequente (`event_type`, `timestamp`, `device`).
- Ajuste `batch_size` conforme capacidade do banco.

Exemplo minimo:

```json
{
  "dispatch_type": "sql",
  "connection_string": "postgresql+asyncpg://user:password@localhost:5432/mydatabase",
  "on_event": "tag",
  "allow_batches": true,
  "batch_size": 500,
  "flush_interval_seconds": 0.1,
  "retry_attempts": 3,
  "retry_backoff_seconds": 0.25,
  "filters": [],
  "query": "INSERT INTO events (device, device_serial_number, epc) VALUES (:device, :device_serial_number, :epc)",
  "params": {
    "device": "{name}",
    "device_serial_number": "{device[serial_number]}",
    "epc": "{data[epc]}"
  }
}
```

### 3) Tipo `mqtt`

Publica eventos em topicos MQTT.

Campos principais:

- `host` e `port`: broker
- `topic`: topico de destino (aceita placeholders)
- `qos`: 0, 1 ou 2
- `retain`: manter mensagem no broker
- `payload`: conteudo publicado

Quando usar:

- IoT em tempo real
- Integracao com brokers e assinantes

Boas praticas:

- Use `qos: 1` para equilibrio entre confiabilidade e custo.
- Use `retain: false` para eventos de telemetria volatil.
- Defina `client_id` estavel para rastreabilidade.

Exemplo minimo:

```json
{
  "dispatch_type": "mqtt",
  "host": "localhost",
  "port": 1883,
  "topic": "smartx/rfid/{name}/{event_type}",
  "on_event": "tag",
  "qos": 1,
  "retain": false,
  "allow_batches": true,
  "batch_size": 500,
  "flush_interval_seconds": 0.1,
  "retry_attempts": 3,
  "retry_backoff_seconds": 0.25,
  "filters": [],
  "payload": {
    "device": "{name}",
    "device_serial_number": "{device[serial_number]}",
    "epc": "{data[epc]}"
  }
}
```

### 4) Tipo `mongodb`

Insere eventos em colecao MongoDB.

Campos principais:

- `connection_string`: URI MongoDB
- `database`: banco
- `collection`: colecao
- `ordered`: controle de ordem em insercoes de lote
- `document`: documento a ser salvo

Quando usar:

- Dados semiestruturados
- Evolucao de schema com menor rigidez

Boas praticas:

- Use indices nos campos de consulta (`event_type`, `timestamp`, `device`, `epc`).
- Se foco for throughput, avaliar `ordered: false`.
- Use filtros para evitar gravar evento desnecessario.

Exemplo minimo:

```json
{
  "dispatch_type": "mongodb",
  "connection_string": "mongodb://localhost:27017",
  "database": "smartx_rfid",
  "collection": "events",
  "ordered": true,
  "on_event": "tag",
  "allow_batches": true,
  "batch_size": 500,
  "flush_interval_seconds": 0.1,
  "retry_attempts": 3,
  "retry_backoff_seconds": 0.25,
  "filters": [],
  "document": {
    "device": "{name}",
    "device_serial_number": "{device[serial_number]}",
    "event_type": "{event_type}",
    "epc": "{data[epc]}"
  }
}
```

## Como configurar da melhor forma

Recomendacoes praticas:

1. Comece com um exemplo da pasta `examples/dispatchers/` e ajuste incrementalmente.
2. Defina `on_event` de forma especifica para evitar volume desnecessario.
3. Aplique `filters` para selecionar apenas eventos relevantes.
4. Use `allow_batches: true` para alto volume.
5. Ajuste lote pensando em latencia x throughput.
6. Para latencia baixa, use `batch_size` menor e `flush_interval_seconds` menor.
7. Para throughput alto, use `batch_size` maior e `flush_interval_seconds` um pouco maior.
8. Mantenha retries habilitados para resiliencia de rede.
9. Evite placeholders de campo (`{data[chave]}`) quando o evento nao for dict.
10. Valide com poucos eventos antes de colocar em producao.

Valores iniciais sugeridos:

- `allow_batches: true`
- `batch_size: 200 a 500`
- `flush_interval_seconds: 0.1 a 0.5`
- `retry_attempts: 3`
- `retry_backoff_seconds: 0.25`

## Eventos comuns para `on_event`

Dependendo da origem do evento, os nomes podem variar. Alguns comuns no sistema:

- `tag`
- `reading`
- `connection`
- `serial_number`
- `add_to_write_list`
- `remove_from_write_list`
- `write_list_empty`
- `write_list_cleared`

Tambem e possivel receber eventos customizados por endpoints de entrada (`/api/v1/receive/*`). Nesses endpoints, o `serial_number` pode ser informado no campo opcional `device_serial_number`; se omitido, e obtido do device conectado com o mesmo nome (quando existir).

## Checklist rapido de validacao

Antes de salvar um novo dispatch, confirme:

- JSON valido
- `dispatch_type` correto
- campos obrigatorios do tipo preenchidos
- `on_event` compativel com os eventos da sua origem
- placeholders compativeis com o formato de `data`
- filtros coerentes
- destino acessivel (URL, banco, broker)
