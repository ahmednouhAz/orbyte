# Orbyte

**Orbyte** is a self-hosted AI platform that puts a full chat, search, and agent
interface in front of your organization's own documents and models. It is built
to run entirely on infrastructure you control — no external API calls are
required, and it works fully offline/air-gapped when paired with a local model
runtime such as [Ollama](https://ollama.com).

---

## Features

- **RAG Search:** Hybrid keyword + vector search across connected documents, with
  citation-backed answers.
- **Custom Agents:** Build agents with their own instructions, knowledge, and
  behavior for different teams or use cases.
- **Web Search:** Optional live web search for up-to-date information.
- **Craft:** A sandboxed code-execution environment for agents to run code,
  analyze data, and generate downloadable artifacts.
- **Connectors:** Index documents from external data sources into a searchable
  knowledge base.
- **Groups & Curators:** Organize users into groups, each with one or more
  curators who manage that group's documents, agents, and shared resources —
  without needing full admin access.
- **Join Links:** Onboard new members with a shareable, group-scoped link
  instead of email invites — a new user opens the link, sets a password, and
  lands directly in the right group. No outbound email or per-person admin
  action required, which makes it practical for fully offline deployments.
- **Role-Based Access Control:** Fine-grained permissions for admins, curators,
  and regular members.
- **Query History:** Audit trail of usage across the organization.

All accounts live in a single shared directory, visible to admins — there is no
per-group account silo.

---

## Running Orbyte locally

Orbyte runs as a set of Docker containers (Postgres, OpenSearch, Redis, MinIO,
the API server, background workers, and the web server).

### Prerequisites

- **Docker** and **Docker Compose**
- An LLM to connect to. For a fully offline setup, install
  [Ollama](https://ollama.com) and pull a model, for example:

  ```bash
  ollama pull qwen2.5:14b-instruct
  ```

  Any Ollama-compatible model works; `qwen2.5:14b-instruct` is a good default
  for general chat and RAG on a single machine with a decent GPU.

### Build and start the stack

There is no separately published "Orbyte" image registry. The services that
actually contain this codebase — `api_server`, `background`, and
`web_server` — always build directly from this repository's `backend/` and
`web/` source, so anyone who clones this repo and runs the command below
gets the real, current Orbyte app, not any external build of it. From
`deployment/docker_compose`:

```bash
docker compose up -d --build
```

Visit `http://localhost:3000` once the containers are up — the first account
you register automatically becomes the admin.

A few supporting services still pull pre-built images rather than compiling
from source, because their code isn't part of this repository (or hasn't
been modified from upstream) and building them locally is a large,
unnecessary cost:

- `inference_model_server` / `indexing_model_server` — unmodified ML/embedding
  code; building from source means installing several GB of torch/CUDA
  dependencies for no behavioral difference.
- `code-interpreter` — its source lives outside this repository entirely.

If you ever do modify `backend/model_server`, uncomment the `build:` block
already present (commented out) next to that service in `docker-compose.yml`.

> **Note:** Docker's build cache can silently reuse a stale image even after
> `--build` reports success. If a change to `api_server`, `background`, or
> `web_server` doesn't seem to show up, confirm the image was actually
> rebuilt:
>
> ```bash
> docker images <image_name> --format "{{.CreatedAt}}"
> ```
>
> and rebuild with `docker compose build --no-cache <service>` if it wasn't.

### Connecting your LLM

Once Orbyte is running, go to **Admin → LLM Providers** and add a provider.
For a local, offline setup with Ollama running on the host machine, point the
provider at your Ollama instance (e.g. `http://host.docker.internal:11434`)
and select the model you pulled (e.g. `qwen2.5:14b-instruct`).

### Setting up groups and onboarding

As an admin, create a group under **Admin → Groups**, assign one or more
curators, and generate a join link from the group's page to share with new
members — they'll be added to that group automatically when they sign up
through the link.

---

## License

Orbyte is built on top of open-source foundations. See [LICENSE](LICENSE) for
license terms and required attribution.
