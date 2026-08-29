"""文档与验收页测试：/docs 资源本地化、/acceptance 页面可用。"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_docs_served_with_local_assets():
    resp = client.get("/docs")
    assert resp.status_code == 200
    # Swagger 资源必须本地化：内嵌浏览器/离线环境加载不到 CDN 会白屏
    assert "/static/swagger/swagger-ui-bundle.js" in resp.text
    assert "cdn.jsdelivr.net" not in resp.text


def test_swagger_assets_served():
    assert client.get("/static/swagger/swagger-ui-bundle.js").status_code == 200
    assert client.get("/static/swagger/swagger-ui.css").status_code == 200


def test_acceptance_page_served():
    resp = client.get("/acceptance")
    assert resp.status_code == 200
    assert "端到端人工验收" in resp.text
    # 页面自包含：不引任何外部资源
    assert "http://" not in resp.text.replace("http://127.0.0.1", "")
    assert "https://" not in resp.text
