from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse
import pandas as pd
import uuid

app = FastAPI()

# 💾 قاعدة بيانات بسيطة (مؤقتة)
users = {}      # email -> password
sessions = {}   # token -> email


# ================= تسجيل حساب =================
@app.post("/register")
def register(email: str, password: str):
    if email in users:
        return {"status": "exists"}

    users[email] = password
    return {"status": "created"}


# ================= تسجيل دخول =================
@app.post("/login")
def login(email: str, password: str):
    if email in users and users[email] == password:
        token = str(uuid.uuid4())
        sessions[token] = email
        return {"status": "success", "token": token}

    return {"status": "error"}


# ================= واجهة =================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body {background:#0f172a;color:white;font-family:Arial;}
.card {background:#1e293b;border-radius:15px;}
.footer {text-align:center;margin-top:20px;color:#38bdf8;}
</style>
</head>

<body>

<div class="container mt-5">

<!-- 🔐 REGISTER -->
<div id="registerBox" class="card p-4 mb-3">
<h4>إنشاء حساب</h4>
<input class="form-control mb-2" id="reg_email" placeholder="الايميل">
<input class="form-control mb-2" id="reg_pass" type="password" placeholder="كلمة المرور">
<button class="btn btn-success" onclick="register()">تسجيل</button>
</div>

<!-- 🔐 LOGIN -->
<div id="loginBox" class="card p-4 mb-4">
<h4>تسجيل الدخول</h4>
<input class="form-control mb-2" id="email" placeholder="الايميل">
<input class="form-control mb-2" id="pass" type="password" placeholder="كلمة المرور">
<button class="btn btn-primary" onclick="login()">دخول</button>
</div>

<!-- 💼 SYSTEM -->
<div id="system" style="display:none;">

<h3 class="text-center mb-4">🚀 نظام مراجعة الفروع</h3>

<div class="row text-center mb-3">
<div class="col"><div class="card p-2">الإجمالي<br><span id="total">0</span></div></div>
<div class="col"><div class="card p-2">مطابق<br><span id="green">0</span></div></div>
<div class="col"><div class="card p-2">متأخر<br><span id="yellow">0</span></div></div>
<div class="col"><div class="card p-2">خطأ<br><span id="red">0</span></div></div>
</div>

<div class="card p-4">

<input class="form-control mb-2" type="file" id="file1">
<input class="form-control mb-3" type="file" id="file2">

<div class="d-flex gap-2">
<button class="btn btn-primary w-50" onclick="send()">تحليل</button>
<button class="btn btn-success w-50" onclick="download()">تحميل Excel</button>
</div>

<table class="table table-bordered mt-4 text-center">
<thead>
<tr>
<th>المبلغ</th>
<th>الحالة</th>
</tr>
</thead>
<tbody id="tableBody"></tbody>
</table>

</div>

</div>

<div class="footer">تم بواسطة محمد علي</div>

</div>

<script>

let token = "";

// 🔐 تسجيل
async function register(){
    let email = document.getElementById("reg_email").value;
    let pass = document.getElementById("reg_pass").value;

    let res = await fetch(`/register?email=${email}&password=${pass}`,{method:"POST"});
    let data = await res.json();

    if(data.status=="created") alert("تم إنشاء الحساب");
    else alert("الايميل مستخدم");
}

// 🔐 دخول
async function login(){
    let email = document.getElementById("email").value;
    let pass = document.getElementById("pass").value;

    let res = await fetch(`/login?email=${email}&password=${pass}`,{method:"POST"});
    let data = await res.json();

    if(data.status=="success"){
        token = data.token;
        document.getElementById("loginBox").style.display="none";
        document.getElementById("registerBox").style.display="none";
        document.getElementById("system").style.display="block";
    }else{
        alert("بيانات غلط");
    }
}

// 📊 تحليل
async function send(){
    let f1=document.getElementById("file1").files[0];
    let f2=document.getElementById("file2").files[0];

    let data=new FormData();
    data.append("file1",f1);
    data.append("file2",f2);

    let res=await fetch(`/compare?token=${token}`,{method:"POST",body:data});
    let json=await res.json();

    let body=document.getElementById("tableBody");
    body.innerHTML="";

    let total=0,green=0,yellow=0,red=0;

    json.forEach(r=>{
        total++;

        let color="";
        if(r.error.includes("🟢")){green++; color="green";}
        else if(r.error.includes("🟡")){yellow++; color="orange";}
        else {red++; color="red";}

        let row=`<tr style="background:${color}">
        <td>${r.amount}</td>
        <td>${r.error}</td></tr>`;

        body.innerHTML+=row;
    });

    document.getElementById("total").innerText=total;
    document.getElementById("green").innerText=green;
    document.getElementById("yellow").innerText=yellow;
    document.getElementById("red").innerText=red;
}

// 📄 تحميل
async function download(){
    let f1=document.getElementById("file1").files[0];
    let f2=document.getElementById("file2").files[0];

    let data=new FormData();
    data.append("file1",f1);
    data.append("file2",f2);

    let res=await fetch(`/download?token=${token}`,{method:"POST",body:data});
    let blob=await res.blob();

    let url=window.URL.createObjectURL(blob);
    let a=document.createElement("a");
    a.href=url;
    a.download="report.xlsx";
    a.click();
}

</script>

</body>
</html>
"""


# ================= تحليل =================
@app.post("/compare")
async def compare(request: Request, file1: UploadFile = File(...), file2: UploadFile = File(...)):
    token = request.query_params.get("token")
    if token not in sessions:
        return {"error": "غير مصرح"}

    df1 = pd.read_excel(file1.file)
    df2 = pd.read_excel(file2.file)

    df1["net"] = df1["مدين"] - df1["دائن"]
    df2["net"] = df2["مدين"] - df2["دائن"]

    df1["التاريخ"] = pd.to_datetime(df1["التاريخ"])
    df2["التاريخ"] = pd.to_datetime(df2["التاريخ"])

    results = []

    for _, r1 in df1.iterrows():
        found = False

        for _, r2 in df2.iterrows():
            if r1["net"] == -r2["net"]:
                diff = abs((r1["التاريخ"] - r2["التاريخ"]).days)

                if diff <= 5:
                    results.append({"amount": r1["net"], "error": "🟢 مطابق"})
                else:
                    results.append({"amount": r1["net"], "error": "🟡 متأخر"})

                found = True
                break

        if not found:
            results.append({"amount": r1["net"], "error": "🔴 خطأ (فرع1)"})

    return results


# ================= Excel =================
@app.post("/download")
async def download(request: Request, file1: UploadFile = File(...), file2: UploadFile = File(...)):
    token = request.query_params.get("token")
    if token not in sessions:
        return {"error": "غير مصرح"}

    df1 = pd.read_excel(file1.file)
    df2 = pd.read_excel(file2.file)

    df1["net"] = df1["مدين"] - df1["دائن"]
    df2["net"] = df2["مدين"] - df2["دائن"]

    results = []

    for n in df1["net"]:
        if -n not in df2["net"].values:
            results.append([n, "فرع1"])

    for n in df2["net"]:
        if -n not in df1["net"].values:
            results.append([n, "فرع2"])

    df = pd.DataFrame(results, columns=["المبلغ", "الفرع"])

    file_path = "report.xlsx"
    df.to_excel(file_path, index=False)

    return FileResponse(file_path, filename="report.xlsx")