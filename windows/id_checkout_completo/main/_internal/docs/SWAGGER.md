[**HOME**](/) | [**LOGS**](/logs) | [**API DOCS**](/docs)

Plataforma de gestão de leitores RFID e roteamento de eventos. Abaixo estão os grupos de endpoints disponíveis expostos pela API REST.

---

Base da API

- Prefixo: `/api/v1`
- Host/porta padrão (local): `http://localhost:5000` (porta configurável em `config/config.json`)

Observações rápidas

- Esta descrição é mostrada na página `/docs` (Swagger UI) acima das rotas.
- Use os schemas e exemplos fornecidos por cada rota para validar entradas/saídas.
- Alguns endpoints podem exigir autenticação ou permissões — verifique `app/core/middleware.py` e os routers.

---

Grupos de endpoints

- **RFID** — `/api/v1/rfid`
  - Operações de leitura/consulta de tags em memória: listagem, estatísticas (GTIN), EPC/TID, limpeza de memória e escrita de EPC.

- **Devices** — `/api/v1/devices`
  - Gerenciamento de leitores: listagem, visualização/atualização de configurações, status e informações de conexão.

- **Application** — `/api/v1/application`
  - Gerenciamento das configurações da aplicação, arquivos de dispositivo e operações de controle (restart/shutdown).

- **Simulator** — `/api/v1/simulator`
  - Injeção de dados sintéticos (tags, lotes, eventos) e geração de GTIN‑14 para testes sem hardware.

- **Receive** — `/api/v1/receive`
  - Recepção de eventos enviados por leitores ou integrações externas (formatos genéricos e específicos). Os endpoints baseados em `EventDeviceSchema` (`x714`, `x-scan`) aceitam `device_serial_number` opcional; se omitido, é resolvido a partir do device conectado com o mesmo nome.

- **License** — `/api/v1/license`
  - Consulta e envio/atualização de licença.

- **Controller** — `/api/v1/controller`
  - Informações de runtime e estado do controlador RFID.

- **Dispatchers** — `/api/v1/dispatchers`
  - Gerenciamento de dispatchers: listar exemplos, obter conteúdo de exemplo, criar/atualizar e deletar dispatches de roteamento (POST/SQL/MQTT/MongoDB).

---

Integrações e dispatchers

- Webhooks HTTP com retry configurável (payload: `{"device": {"name", "serial_number"}, "event_type", "event_data"}`)
- Integração XTRACK
- Persistência via SQLAlchemy (SQLite/MySQL/Postgres)
- Arquivos de dispatcher: `config/dispatchers/` (exemplos em `examples/dispatchers/`)

---

Para detalhes de schemas, parâmetros e códigos de resposta, utilize a interface interativa em `/docs`.
