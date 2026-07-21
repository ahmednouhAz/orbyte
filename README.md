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

### Start the stack

From `deployment/docker_compose`:

```bash
docker compose up -d
```

This pulls the pre-built images and starts the full stack. Visit
`http://localhost:3000` once the containers are up — the first account you
register automatically becomes the admin.

### Building from source changes

If you've made local changes and want them reflected in the running app,
build the images from source instead of pulling pre-built ones:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-build.yml -f docker-compose.local-build-backend.yml up -d --build
```

- `docker-compose.local-build.yml` builds the web server from source.
- `docker-compose.local-build-backend.yml` builds the API server and
  background workers from source.

After rebuilding, confirm the new image was actually used (Docker's build
cache can silently reuse a stale image):

```bash
docker images <image_name> --format "{{.CreatedAt}}"
```

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
