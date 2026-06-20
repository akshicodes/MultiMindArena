# MultiMind Arena Completion Plan

This implementation plan details the steps required to complete the MultiMind Arena LLM Debate System. The goal is to evolve the current skeleton application into a fully functional, real-time multi-agent debate platform with a live analytics dashboard, a comprehensive test suite, Docker configuration, and clean API key rotation.

## User Review Required

> [!IMPORTANT]
> The following architectural decisions require your review:
>
> 1. **Codebase Directory Layout**: The assignment outlines a structure using `backend/`, `frontend/`, and `tests/` folders in the workspace root. Currently, the code is structured under `app/` and `app/static/`. We propose restructuring the project to match the assignment guidelines exactly, making it easier to submit the final zip.
> 2. **OpenRouter vs. Direct Clients**: The assignment asks for direct client integrations for OpenAI (GPT-4o), Anthropic (Claude 3), Google (Gemini 1.5), and Mistral. We can either fully switch to these direct SDKs/endpoints or keep the current OpenRouter API as a configurable fallback client.
> 3. **Word Cloud & Charts**: We will use Chart.js for rendering leaderboards and sentiment trends in the frontend, and standard CSS/JS word cloud algorithms for the top words panel.

## Open Questions

> [!WARNING]
> Please review these questions and provide your feedback before we proceed:
> 
> 1. **API Keys Availability**: Do you have active API keys for OpenAI, Anthropic, Gemini, and Mistral? If not, do you want to keep using the OpenRouter API key for all participants under the hood while simulating separate provider profiles for the grading rubric?
> 2. **Bonus Challenges**: Which optional bonus challenges should we include? We recommend implementing the **Persona Override API (+8 Marks)** and **Debate Export to PDF (+8 Marks)** as they add high visual value and are straightforward to build.

---

## Proposed Changes

### 1. Directory Structure Restructuring
We propose to reorganize the codebase to follow the layout specified in the assignment details:
* Move `app/` to `backend/`.
* Move `app/static/` to `frontend/`.
* Move `app/test_debate_engine.py` and other test scripts into a root `tests/` directory.

---

### 2. LLM Clients & Key Rotation Component

#### [NEW] [openai_client.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/llm_clients/openai_client.py)
* Create `OpenAIClient` inheriting from `BaseLLMClient` to communicate directly with OpenAI's API.
* Implement round-robin key rotation for variables `OPENAI_API_KEY_1`, `OPENAI_API_KEY_2` etc.

#### [NEW] [anthropic_client.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/llm_clients/anthropic_client.py)
* Create `AnthropicClient` for direct integration with Anthropic's Claude models, including key rotation.

#### [NEW] [gemini_client.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/llm_clients/gemini_client.py)
* Create `GeminiClient` for direct integration with Google Generative AI models.

#### [NEW] [mistral_client.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/llm_clients/mistral_client.py)
* Create `MistralClient` for Mistral AI models.

#### [MODIFY] [participants.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/participants.py)
* Rename current default participants to match the validation schema: `GPT-4o`, `Claude`, `Gemini`, and `Mistral`.
* Assign them their corresponding client instances instead of all using OpenRouter.

---

### 3. Debate Engine & Turn Scheduling

#### [MODIFY] [engine.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/engine.py)
* **Pacing Delays**: Add `asyncio.sleep` between turns using environment variable durations (`MIN_TURN_DELAY_SECONDS` and `MAX_TURN_DELAY_SECONDS`).
* **Interrupt Mechanic**: Add a check on every turn cycle; with a 10% probability (`INTERRUPT_PROBABILITY`), pick a participant to interrupt with a short response.
* **Dead Air Prevention**: Implement a timeout around client generation. If the selected speaker takes > 15s or raises an error, immediately select a fallback speaker.

#### [MODIFY] [scheduler.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/scheduler.py)
* **User Priority Override**: Implement logic to guarantee the next two speakers address the user if a user message has just been received.
* **Turn Weights**: Enhance weights calculation to reduce chances of consecutive speakers.

---

### 4. Real-Time WebSockets Communication

#### [MODIFY] [app.js](file:///c:/Users/sonakshi/Desktop/MultiMindArena/frontend/app.js)
* Replace REST polling (`pollSessionMessages`) with a native `WebSocket` client pointing to `/sessions/{id}/ws`.
* Process `message.stream` events to show token-by-token response streams in the chat interface.
* Render a typing/thinking indicator when `speaker.thinking` event is received.

#### [MODIFY] [index.html](file:///c:/Users/sonakshi/Desktop/MultiMindArena/frontend/index.html)
* Add a connection status badge (e.g. Connected/Disconnected) at the top of the interface.

---

### 5. Live Analytics Engine

#### [NEW] [sentiment.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/analytics/sentiment.py)
* Implement VADER and TextBlob sentiment analysis. Every incoming debate message will be analyzed and assigned a score between `-1.0` and `1.0`.

#### [NEW] [tagging.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/analytics/tagging.py)
* Implement rule-based/regex tagging for classifying statements (e.g. `["sarcasm", "counter-claim", "question", "concession"]`).

#### [NEW] [aggregator.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/analytics/aggregator.py)
* Create an async background task runner that executes every 10 seconds.
* Computes and updates the `analytics` collection in MongoDB: rolling average sentiment per LLM, aggression index, topic drift, win scores, streaks, and word frequencies.

#### [NEW] [analytics.js](file:///c:/Users/sonakshi/Desktop/MultiMindArena/frontend/analytics.js)
* Implement the dashboard charts script using Chart.js.
* Update charts when WebSocket broadcasts `analytics_update` events.

#### [MODIFY] [index.html](file:///c:/Users/sonakshi/Desktop/MultiMindArena/frontend/index.html)
* Restructure layout to include a side panel for charts:
  * Horizontal bar chart for message leaderboard.
  * Line graph for sentiment over time.
  * Gauges / badges for aggression index, topic drift, win predictor, and streaking participant.
  * Word cloud panel.

---

### 6. Infrastructure, Testing & Scripts

#### [MODIFY] [seed_db.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/backend/scripts/seed_db.py)
* Fix absolute/relative imports and add a command-line interface to seed the collections.

#### [NEW] [docker-compose.yml](file:///c:/Users/sonakshi/Desktop/MultiMindArena/docker-compose.yml)
* Define a multi-container Docker environment:
  * `db`: MongoDB database image with mapped volumes.
  * `web`: FastAPI app container running backend code, exposing port 8000.

#### [NEW] [test_db.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/tests/test_db.py)
* Write tests verifying session, message, and topics database CRUD operations.

#### [NEW] [test_llm_clients.py](file:///c:/Users/sonakshi/Desktop/MultiMindArena/tests/test_llm_clients.py)
* Write tests mocking response outputs and key rotation behaviors.

---

## Verification Plan

### Automated Tests
Execute the pytest suite covering LLM clients, DB operations, scheduling, and socket events:
```bash
poetry run pytest tests/
# or
pipenv run pytest tests/
# or
python -m pytest tests/
```

### Manual Verification
1. Launch MongoDB locally and seed the database using `python backend/scripts/seed_db.py`.
2. Start the FastAPI backend server.
3. Open the UI, configure a debate topic, select the rounds, and start the debate.
4. Verify token-by-token streaming is visible, delays are present, and the sidebar charts update in real-time.
5. Inject a user message and ensure models respond dynamically.
