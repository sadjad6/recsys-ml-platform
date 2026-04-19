# Task 11: Streamlit Frontend

## Goal

Build a demo-ready Streamlit UI that allows selecting users, viewing recommendations with experiment group information, simulating user interactions, and sending real events to the backend.

## Context

The frontend is the demo layer — it makes the entire system tangible. It must be visually clean, interactive, and demonstrate the full loop: select user → see recommendations (with A/B group info) → simulate interactions → events flow through the system → recommendations update.

## Requirements

### Functional
- User selector (dropdown or search)
- Recommendations display with item details and scores
- Experiment group indicator (which model version is serving)
- Interaction simulator: click, view, and rate buttons for each item
- Event submission to backend (via API Gateway)
- Real-time feedback: show event was submitted successfully

### Technical Constraints
- Streamlit (mandatory per spec)
- Communicates with API Gateway (not directly with services)
- Must be containerized
- Visually clean and demo-ready

## Implementation Steps

### Step 1: Main Application

Create `frontend/streamlit_app.py`:

```python
import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="RecSys Platform",
    page_icon="🎯",
    layout="wide"
)

# Sidebar: User Selection
# Main area: Recommendations + Interactions
# Footer: System Status
```

### Step 2: User Selection Panel

Sidebar component:

```python
# 1. Fetch user list from API Gateway: GET /api/v1/users
# 2. Display as selectbox with user_id and username
# 3. On selection, store in st.session_state
# 4. Show user details: total interactions, last active, preferences
```

### Step 3: Recommendations Display

Main panel:

```python
# 1. Call API Gateway: GET /api/v1/recommendations?user_id=X
# 2. Display experiment info:
#    - Experiment group badge (A/B) with color coding
#    - Model version being used
#    - Cache hit indicator
#    - Response time
# 3. Display recommendations as cards:
#    - Item name/ID
#    - Score (relevance)
#    - Rank position
#    - Category tag
# 4. Use st.columns for card grid layout (3 columns)
```

### Step 4: Interaction Simulator

For each recommended item, add action buttons:

```python
# Per item card:
# - 👁️ View button → sends view event
# - 👆 Click button → sends click event
# - ⭐ Rate slider (1-5) + submit → sends rating event
#
# On button click:
# 1. POST /api/v1/events with:
#    {
#      "user_id": selected_user,
#      "item_id": item_id,
#      "event_type": "click" | "view" | "rating",
#      "rating": 4.0  (only for ratings)
#    }
# 2. Show success toast: "Event submitted ✓"
# 3. Optionally refresh recommendations
```

### Step 5: System Status Panel

Bottom section or sidebar:

```python
# 1. Health check all services via API Gateway: GET /health
# 2. Display service status indicators (green/red dots)
# 3. Show key metrics:
#    - Events processed (today)
#    - Active experiments
#    - Current model version
#    - Cache hit rate
```

### Step 6: Experiment Dashboard Tab

Add a second tab/page for experiment monitoring:

```python
# Tab 2: A/B Testing Dashboard
# 1. Fetch active experiments: GET /api/v1/experiments
# 2. For each experiment, show:
#    - Control vs Treatment metrics (CTR, engagement)
#    - Sample sizes per group
#    - Statistical significance indicator
#    - Bar chart comparison (using st.bar_chart or plotly)
# 3. Traffic split visualization (pie chart)
```

### Step 7: Styling

Create `frontend/style.css` or use `st.markdown` with custom CSS:

```python
# Clean, modern look:
# - Dark sidebar with brand colors
# - Card-based layout for recommendations
# - Color-coded badges for experiment groups
# - Consistent spacing and typography
# - Loading spinners for API calls
```

### Step 8: Docker Configuration

Create `frontend/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

`requirements.txt`:
```
streamlit>=1.32.0
requests>=2.31.0
plotly>=5.18.0
pandas>=2.2.0
```

Add to `docker-compose.yml`:

```yaml
streamlit:
  build: ./frontend
  ports:
    - "8501:8501"
  environment:
    - API_GATEWAY_URL=http://api-gateway:8000
  depends_on:
    - api-gateway
```

## Deliverables

| File | Purpose |
|------|---------|
| `frontend/streamlit_app.py` | Main Streamlit application |
| `frontend/style.css` | Custom styling |
| `frontend/requirements.txt` | Python dependencies |
| `frontend/Dockerfile` | Container definition |
| Updated `docker-compose.yml` | Streamlit service |

## Validation

1. Start frontend: `docker-compose up -d streamlit`
2. Open `http://localhost:8501` in browser
3. Select a user → recommendations load and display
4. Verify experiment group badge is shown
5. Click "View" on an item → success toast appears
6. Click "Rate" with a value → event submitted
7. Verify events appear in Kafka (check with consumer)
8. Refresh recommendations → verify they reflect interactions
9. Check system status panel → all services show green
10. Navigate to A/B dashboard tab → experiment metrics display
11. Visual check: layout is clean, no broken elements, mobile-friendly
