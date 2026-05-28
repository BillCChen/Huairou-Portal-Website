#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_V1_CONTENT_SMOKE_PORT:-18240}"
HOST="${PORTAL_V1_CONTENT_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_V1_CONTENT_SMOKE_RUNTIME_DIR:-.runtime-logs/v1-content-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[v1-content-smoke] $*"
}

fail() {
  echo "[v1-content-smoke] ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [ -n "${API_PID}" ] && ps -p "${API_PID}" >/dev/null 2>&1; then
    log "stopping API pid ${API_PID}"
    kill "${API_PID}" || true
    wait "${API_PID}" 2>/dev/null || true
    if ps -p "${API_PID}" >/dev/null 2>&1; then
      kill -9 "${API_PID}" || true
      wait "${API_PID}" 2>/dev/null || true
    fi
  fi
}

trap cleanup EXIT

if [ "${PORT}" = "8000" ]; then
  fail "port 8000 is reserved; refusing to use it for local smoke"
fi

if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN || true
  fail "port ${PORT} is already in use; refusing to stop unknown process"
fi

python_minor() {
  local python_bin="$1"
  "${python_bin}" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

candidate_list() {
  if [ -n "${PYTHON_OVERRIDE}" ]; then
    echo "${PYTHON_OVERRIDE}"
    return 0
  fi
  printf '%s\n' python3.13 python3.12 python3.11
}

prepare_venv() {
  local python_bin="$1"
  local python_mm

  if ! command -v "${python_bin}" >/dev/null 2>&1; then
    log "skipping ${python_bin}: not found"
    return 1
  fi

  python_mm="$(python_minor "${python_bin}")"
  case "${python_mm}" in
    3.11|3.12|3.13) ;;
    *)
      log "skipping ${python_bin}: unsupported Python ${python_mm}"
      return 1
      ;;
  esac

  VENV_DIR="${RUNTIME_DIR}/backend-venv-py${python_mm//./}"
  mkdir -p "${RUNTIME_DIR}"

  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    log "creating venv at ${VENV_DIR}"
    "${python_bin}" -m venv "${VENV_DIR}" || return 1
  fi

  log "installing backend requirements"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/python" -m pip install -r apps/api-server/requirements.txt >/dev/null
  return 0
}

selected_python=""
for candidate in $(candidate_list); do
  if prepare_venv "${candidate}"; then
    selected_python="${candidate}"
    break
  fi
  if [ -n "${PYTHON_OVERRIDE}" ]; then
    fail "PORTAL_BACKEND_PYTHON=${PYTHON_OVERRIDE} failed"
  fi
done

if [ -z "${selected_python}" ]; then
  fail "no compatible Python interpreter could create a backend venv and install requirements"
fi

DB_PATH="${RUNTIME_DIR}/portal_v1_content_smoke.sqlite3"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"
LOG_PATH="${RUNTIME_DIR}/api.log"
PID_PATH="${RUNTIME_DIR}/api.pid"

rm -f "${DB_PATH}"
mkdir -p "${UPLOAD_DIR}"

log "starting API at ${BASE_URL}"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="disabled" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
) > "${LOG_PATH}" 2>&1 &

API_PID="$!"
echo "${API_PID}" > "${PID_PATH}"

API_READY=0
for i in $(seq 1 30); do
  if curl -sS --max-time 2 "${BASE_URL}/healthz" >/dev/null 2>&1; then
    API_READY=1
    log "API became reachable on attempt ${i}"
    break
  fi
  sleep 1
done

if [ "${API_READY}" -ne 1 ]; then
  echo "--- API log ---"
  cat "${LOG_PATH}" || true
  fail "API did not become ready on ${BASE_URL}"
fi

BASE_URL="${BASE_URL}" DB_PATH="${DB_PATH}" ROOT_DIR="${ROOT_DIR}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base_url = os.environ["BASE_URL"]
root_dir = Path(os.environ["ROOT_DIR"])
db_path = os.environ["DB_PATH"]


def request_json(path: str, method: str = "GET", body: dict | None = None, token: str | None = None, expected: int = 200):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        status = exc.code
        payload_text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(payload_text) if payload_text else {}
    if status != expected:
        raise SystemExit(f"{method} {path} returned {status}, expected {expected}")
    return payload


def data(path: str):
    return request_json(path)["data"]


def assert_true(condition: bool, message: str):
    if not condition:
        raise SystemExit(message)


health = request_json("/healthz")
assert_true(health["data"]["status"] == "ok", "health payload mismatch")

home = data("/api/v1/public/home")
for key in ["banners", "news", "cases", "about", "site_settings"]:
    assert_true(key in home, f"home missing {key}")
assert_true(len(home["banners"]) >= 1, "home banners are empty")
assert_true(len(home["news"]) >= 1, "home news are empty")
assert_true(len(home["cases"]) >= 1, "home cases are empty")
assert_true(home["site_settings"].get("site_profile", {}).get("contact_email"), "site profile email missing")
assert_true(isinstance(home["site_settings"].get("home_stats"), list), "home stats missing")

news_categories = data("/api/v1/public/categories?type=news")
case_categories = data("/api/v1/public/categories?type=case")
assert_true(news_categories, "news categories are empty")
assert_true(case_categories, "case categories are empty")

tags = data("/api/v1/public/tags")
assert_true(tags, "public tags are empty")

news_list = data("/api/v1/public/news?page=1&page_size=5")
assert_true(news_list["items"], "news list is empty")
first_news = news_list["items"][0]
assert_true(first_news.get("category_name"), "news category metadata missing")
assert_true("tag_ids" in first_news, "news tag metadata missing")

keyword_news = data(f"/api/v1/public/news?keyword={quote('平台')}")
assert_true(keyword_news["total"] >= 1, "news keyword search returned no result")

category_news = data(f"/api/v1/public/news?category={quote(news_categories[0]['slug'])}")
assert_true(category_news["total"] >= 1, "news category filter returned no result")

news_detail = data(f"/api/v1/public/news/{first_news['slug']}")
assert_true(news_detail["article"]["slug"] == first_news["slug"], "news detail slug mismatch")

case_list = data("/api/v1/public/cases?page=1&page_size=5")
assert_true(case_list["items"], "case list is empty")
first_case = case_list["items"][0]
assert_true(first_case.get("partner_name"), "case partner missing")
assert_true(first_case.get("benefits"), "case benefits missing")
assert_true(first_case.get("category_name"), "case category metadata missing")

case_detail = data(f"/api/v1/public/cases/{first_case['slug']}")
assert_true(case_detail["case"]["slug"] == first_case["slug"], "case detail slug mismatch")
assert_true(case_detail["case"].get("result_blocks"), "case result blocks missing")

about = data("/api/v1/public/pages/about")
about_titles = {item.get("title") for item in about.get("blocks", [])}
for title in ["使命愿景", "发展战略", "治理结构", "联系方式"]:
    assert_true(title in about_titles, f"about block missing {title}")

leaders = data("/api/v1/public/leaders")
assert_true(leaders, "leaders are empty")

settings = data("/api/v1/public/settings")
assert_true(settings.get("site_profile", {}).get("contact_email"), "public settings contact email missing")

sys.path.insert(0, str(root_dir / "apps/api-server"))
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
from app.db.models import Article, Category
from app.db.session import SessionLocal

with SessionLocal() as db:
    category = db.query(Category).filter(Category.type == "article").first()
    article = Article(
        title="Draft content smoke item",
        slug="draft-content-smoke-item",
        summary="This draft must not be exposed by public endpoints.",
        content_html="<p>Draft only.</p>",
        category_id=category.id if category else None,
        source="Smoke",
        author="Smoke",
        publish_at=datetime.now(UTC),
        status="draft",
    )
    db.add(article)
    db.commit()

request_json("/api/v1/public/news/draft-content-smoke-item", expected=404)
draft_search = data("/api/v1/public/news?keyword=Draft%20content%20smoke")
assert_true(draft_search["total"] == 0, "draft article leaked through public search")

login = request_json(
    "/api/v1/auth/login/password",
    method="POST",
    body={"username": "admin", "password": "ChangeMe123!"},
)["data"]
admin_token = login["access_token"]
for path in [
    "/api/v1/admin/articles",
    "/api/v1/admin/cases",
    "/api/v1/admin/pages",
    "/api/v1/admin/banners",
    "/api/v1/admin/categories",
    "/api/v1/admin/tags",
    "/api/v1/admin/leaders",
    "/api/v1/admin/settings",
]:
    request_json(path, token=admin_token)

print("v1 content smoke checks passed")
PY

log "v1 content smoke passed"
