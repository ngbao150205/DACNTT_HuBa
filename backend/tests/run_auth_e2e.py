"""Browser + Mailpit + real model + PostgreSQL in a disposable auth schema.

Requires running Compose services and built application images. A separate,
disposable browser-test image is built on first use. Never calls Lazada or modifies app user data.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
RUN = uuid.uuid4().hex[:12]
SCHEMA = "auth_e2e_" + RUN
PREFIX = "duancntt-auth-test-" + RUN
BACKEND, FRONTEND, MAIL, CRAWLER, BROWSER = (PREFIX + suffix for suffix in ("-backend", "-frontend", "-mail", "-crawler", "-browser"))
NETWORK = os.getenv("AUTH_TEST_DOCKER_NETWORK", "duancntt_default")


def docker(*args, check=True, input=None):
    result = subprocess.run(["docker", *map(str,args)], cwd=ROOT, text=True, input=input,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError(f"Docker {args[0]} failed: {result.stderr[-1800:]}")
    return result.stdout.strip()


def sql(drop=False):
    statement = f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE' if drop else f'CREATE SCHEMA "{SCHEMA}"'
    code = f'from database.connection import engine; from sqlalchemy import text;\nwith engine.begin() as c: c.execute(text({statement!r}))'
    docker("exec", "sentiment-backend", "python", "-c", code)


schema_created = False
cookie_file = None
try:
    if not docker("image", "ls", "-q", "duancntt-browser-test"):
        print("Building optional browser test image...", flush=True)
        docker("build", "-t", "duancntt-browser-test", "-f", "backend/tests/Dockerfile.browser", ".")
    docker("run", "--rm", "-d", "--name", BROWSER, "--network", NETWORK, "--init", "--shm-size", "1gb",
           "--security-opt", "seccomp="+str(ROOT/"backend/tests/browser-security/chromium-seccomp.json"),
           "duancntt-browser-test", "python", "-c", "import time; time.sleep(3600)")
    sql(); schema_created = True
    docker("run", "--rm", "-d", "--name", MAIL, "--network", NETWORK, "axllent/mailpit:v1.30.5")
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as handle:
        handle.write("LAZADA_COOKIE=synthetic-e2e-cookie\n")
        cookie_file = handle.name
    os.chmod(cookie_file, 0o644)
    docker("run", "--rm", "-d", "--name", CRAWLER, "--network", NETWORK,
           "-e", "LAZADA_ENV_FILE=/tmp/crawler-test.env",
           "-e", "LAZADA_EXPORT_DIR=/tmp/crawler-test-exports",
           "-v", cookie_file+":/tmp/crawler-test.env:ro",
           "-v", str(ROOT/"crawler-service/tests/cookie_source_fixture.py")+":/tmp/cookie_fixture.py:ro",
           "-e", "PYTHONPATH=/app/crawler-service", "duancntt-crawler-service", "python", "/tmp/cookie_fixture.py")
    code = f'''import os
from sqlalchemy.engine import make_url
url=make_url(os.environ["DATABASE_URL"]).update_query_dict({{"options":"-csearch_path={SCHEMA}"}})
os.environ["DATABASE_URL"]=url.render_as_string(hide_password=False)
import uvicorn
uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
'''
    docker("run", "--rm", "-d", "--name", BACKEND, "--network", NETWORK,
           "--env-file", ROOT / ".env",
           "-e", f"CRAWLER_SERVICE_URL=http://{CRAWLER}:8002", "-e", f"AUTH_FRONTEND_URL=http://{BACKEND}:5173",
           "-e", "AUTH_COOKIE_SECURE=false", "-e", f"SMTP_HOST={MAIL}", "-e", "SMTP_PORT=1025",
           "duancntt-backend", "python", "-c", code)
    docker("run", "--rm", "-d", "--name", FRONTEND, "--network", "container:" + BACKEND,
           "-e", f"__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS={BACKEND}", "duancntt-frontend")
    probe = "import urllib.request; urllib.request.urlopen('http://localhost:8000/'); urllib.request.urlopen('http://localhost:5173/')"
    deadline = time.monotonic() + 60
    while True:
        try:
            docker("exec", BACKEND, "python", "-c", probe); break
        except RuntimeError:
            if time.monotonic() > deadline: raise
            time.sleep(1)
    xlsx_code = "import io,base64; from openpyxl import Workbook; b=Workbook(); s=b.active; s.append(['review_id','content','rating']); s.append(['xlsx-1','Sản phẩm tốt đúng mô tả',5]); f=io.BytesIO(); b.save(f); print(base64.b64encode(f.getvalue()).decode())"
    xlsx_base64 = docker("run", "--rm", "duancntt-backend", "python", "-c", xlsx_code)
    browser_code = r'''
import json, re, time, io, csv, base64
from playwright.sync_api import sync_playwright, expect
BASE=__BASE__
API=BASE.replace(':5173', ':8000')
MAIL=__MAIL__
PASSWORD='test-password-123'
URL='https://www.lazada.vn/products/test-i987654321.html'
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chromium', headless=True, chromium_sandbox=True)
    contexts=[]
    def register(email, name):
        context=browser.new_context(viewport={'width':1440,'height':1000}); contexts.append(context)
        page=context.new_page(); page.goto(BASE+'/register')
        page.get_by_label('Họ và tên').fill(name)
        page.locator('input[type=email]').fill(email)
        fields=page.locator('input[type=password]'); fields.nth(0).fill(PASSWORD); fields.nth(1).fill(PASSWORD)
        page.get_by_role('button', name='Đăng ký', exact=True).click()
        page.wait_for_url(BASE+'/')
        expect(page.get_by_role('link', name=name, exact=True)).to_be_visible()
        return context,page
    def upload(page, content, excel=False):
        page.goto(BASE+'/analyze')
        page.get_by_role('tab', name='Tải file CSV / Excel').click()
        expect(page.locator('#product-url')).to_have_count(0)
        expect(page.get_by_role('tab')).to_have_count(2)
        page.get_by_label('Tên sản phẩm',exact=True).fill('Tai nghe kiểm thử')
        buffer=io.StringIO(); writer=csv.writer(buffer); writer.writerow(['review_id','content','rating']); writer.writerow(['shared-review-id',content,5])
        data=buffer.getvalue().encode()
        if excel: data=base64.b64decode(__XLSX__)
        page.locator('input[type=file]').set_input_files({'name':'reviews.xlsx' if excel else 'reviews.csv','mimeType':'application/octet-stream','buffer':data})
        with page.expect_response(lambda r:'/collections/import?' in r.url) as response:
            page.get_by_role('button', name='Tải file và phân tích').click()
        assert response.value.status==200, response.value.status
        result=response.value.json()
        expect(page.get_by_text('Đã nhập dữ liệu thành công', exact=True)).to_be_visible()
        if excel: page.screenshot(path='/tmp/duancntt-file-import.png',full_page=True)
        page.get_by_role('button', name='Xem kết quả phân tích').click()
        page.wait_for_url('**/dashboard')
        return result['product_db_id']
    anon=browser.new_context(); contexts.append(anon)
    page=anon.new_page(); page.goto(BASE+'/history'); page.wait_for_url('**/login')
    a,pa=register('browser-a@example.com','Người A')
    id_a=upload(pa,'Sản phẩm tốt giao hàng nhanh của người A')
    assert upload(pa,'Sản phẩm tốt giao hàng nhanh của người A')==id_a
    assert a.request.get(f'{API}/products/{id_a}/reviews').json()['pagination']['total_reviews']==1
    assert upload(pa,'',excel=True)==id_a
    assert a.request.get(f'{API}/products/{id_a}/reviews').json()['pagination']['total_reviews']==2
    pa.goto(BASE+'/analyze'); pa.get_by_label('URL sản phẩm Lazada').fill(URL)
    with pa.expect_response(lambda r:'/products/analyze' in r.url) as analysis:
        pa.get_by_role('button',name='Phân tích sản phẩm',exact=True).click()
    assert analysis.value.status==200
    source=analysis.value.json()
    assert source['crawl_source']=='cookie_star_filter'
    assert source['crawl_status']=='FULL' and source['crawled_reviews']==10
    assert {r['rating'] for r in source['reviews']}=={1,2,3,4,5}
    assert 'synthetic-e2e-cookie' not in json.dumps(source)
    url_id=source['product_db_id']
    pa.wait_for_url('**/dashboard')
    key=a.request.post(API+'/auth/api-token',data={}).json()['token']
    b,pb=register('browser-b@example.com','Người B')
    id_b=upload(pb,'Sản phẩm rất tốt đúng mô tả của người B')
    assert id_a!=id_b
    assert {p['id'] for p in a.request.get(API+'/products').json()['products']}=={id_a,url_id}
    assert [p['id'] for p in b.request.get(API+'/products').json()['products']]==[id_b]
    for suffix in ['analysis','reviews','histories']:
        assert b.request.get(f'{API}/products/{id_a}/{suffix}').status==404
    # A second valid session must be revoked by password recovery.
    other=browser.new_context(); contexts.append(other)
    assert other.request.post(API+'/auth/login',data={'email':'browser-a@example.com','password':PASSWORD}).status==200
    mirror=a.new_page(); mirror.goto(BASE+'/history')
    expect(mirror.get_by_role('link',name='Người A',exact=True)).to_be_visible()
    pa.get_by_role('button',name='Đăng xuất').click(); pa.wait_for_url('**/login')
    mirror.wait_for_url('**/login')
    pa.get_by_role('link',name='Quên mật khẩu?').click()
    pa.wait_for_url('**/forgot-password')
    expect(pa.get_by_role('heading',name='Quên mật khẩu?',exact=True)).to_be_visible()
    pa.locator('input[type=email]').fill('browser-a@example.com')
    pa.get_by_role('button',name='Gửi liên kết').click()
    expect(pa.get_by_role('status')).to_contain_text('Nếu email đã được đăng ký')
    deadline=time.monotonic()+20; link=None
    while time.monotonic()<deadline:
        messages=a.request.get(MAIL+'/api/v1/messages').json()['messages']
        if messages:
            detail=a.request.get(MAIL+'/api/v1/message/'+messages[0]['ID']).json()
            match=re.search(r'http://[^\s<>]+/reset-password#token=[A-Za-z0-9_-]+',detail.get('Text',''))
            if match: link=match.group(); break
        time.sleep(.5)
    assert link, 'Mailpit did not receive a reset link'
    pa.goto(link)
    fields=pa.locator('input[type=password]'); fields.nth(0).fill('new-browser-password-123'); fields.nth(1).fill('new-browser-password-123')
    pa.get_by_role('button',name='Lưu mật khẩu mới').click()
    expect(pa.get_by_role('status')).to_contain_text('Đã đặt lại mật khẩu')
    assert '#' not in pa.url
    assert other.request.get(API+'/auth/me').status==401
    assert a.request.get(API+'/collections/status',headers={'Authorization':'Bearer '+key}).status==401
    pa.get_by_role('link',name='Trở về đăng nhập').click()
    pa.locator('input[type=email]').fill('browser-a@example.com')
    pa.locator('input[type=password]').fill('new-browser-password-123')
    pa.get_by_role('button',name='Đăng nhập',exact=True).click(); pa.wait_for_url(BASE+'/')
    pa.reload(); expect(pa.get_by_role('link',name='Người A',exact=True)).to_be_visible()
    pa.goto(BASE+'/history'); expect(pa.get_by_role('heading',name='Lịch sử phân tích',exact=True)).to_be_visible()
    # UI screenshot is optional evidence, no password/token displayed.
    pa.screenshot(path='/tmp/duancntt-auth-history.png',full_page=True)
    mobile=browser.new_context(viewport={'width':390,'height':844}); contexts.append(mobile)
    mp=mobile.new_page(); mp.goto(BASE+'/login'); expect(mp.get_by_role('button',name='Đăng nhập',exact=True)).to_be_visible()
    assert mp.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    mp.screenshot(path='/tmp/duancntt-auth-login.png',full_page=True)
    for context in contexts: context.close()
    browser.close()
print('PASS browser CSV/XLSX name-only merging, URL via supplied cookie crawler with all five stars, real AI, IDOR 404, Mailpit reset, credential revocation, session reload, cross-tab logout and mobile auth layout')
'''.replace('__XLSX__',repr(xlsx_base64)).replace('__BASE__',repr(f'http://{BACKEND}:5173')).replace('__MAIL__',repr(f'http://{MAIL}:8025'))
    print(docker("exec", "-i", BROWSER, "python", "-", input=browser_code), flush=True)
finally:
    for name in (FRONTEND, BACKEND, MAIL, CRAWLER, BROWSER): docker("rm", "-f", name, check=False)
    if schema_created: sql(drop=True)
    if cookie_file: Path(cookie_file).unlink(missing_ok=True)
