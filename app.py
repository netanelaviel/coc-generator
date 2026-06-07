import io
import os
import bcrypt
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, send_file, flash
)
from supabase import create_client, Client
from generate_pdf import generate_coc

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_user(username: str):
    res = supabase.table("coc_users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None


def logged_in():
    return "user" in session


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user(username)
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            session["user"] = username
            return redirect(url_for("index"))
        error = "שם משתמש או סיסמה שגויים"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if not logged_in():
        return redirect(url_for("login"))

    error = None
    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
        if not sku:
            error = "יש להזין מק\"ט"
        else:
            res = supabase.table("coc_products").select("*").eq("sku", sku).execute()
            if not res.data:
                error = f'מק"ט {sku} לא נמצא במערכת'
            else:
                product = res.data[0]

                # Log the generation
                supabase.table("coc_logs").insert({
                    "username": session["user"],
                    "sku": sku,
                    "model": product["model"],
                }).execute()

                pdf_bytes = generate_coc(sku, product["model"])
                filename = f"COC_{sku}_{datetime.now().strftime('%Y%m%d')}.pdf"
                return send_file(
                    io.BytesIO(pdf_bytes),
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=filename,
                )

    return render_template("index.html", user=session["user"], error=error)


# ── Admin: product management ─────────────────────────────────────────────────

@app.route("/admin")
def admin():
    if not logged_in():
        return redirect(url_for("login"))
    res = supabase.table("coc_users").select("role").eq("username", session["user"]).execute()
    if not res.data or res.data[0].get("role") != "admin":
        return redirect(url_for("index"))

    products = supabase.table("coc_products").select("*").order("sku").execute().data
    users = supabase.table("coc_users").select("username,role,created_at").order("username").execute().data
    logs = supabase.table("coc_logs").select("*").order("created_at", desc=True).limit(50).execute().data
    return render_template("admin.html", products=products, users=users, logs=logs)


@app.route("/admin/product/add", methods=["POST"])
def add_product():
    if not logged_in():
        return redirect(url_for("login"))
    sku = request.form.get("sku", "").strip()
    model = request.form.get("model", "").strip()
    description = request.form.get("description", "").strip()
    if sku and model:
        supabase.table("coc_products").upsert({
            "sku": sku, "model": model, "description": description
        }).execute()
    return redirect(url_for("admin"))


@app.route("/admin/product/delete/<sku>", methods=["POST"])
def delete_product(sku):
    if not logged_in():
        return redirect(url_for("login"))
    supabase.table("coc_products").delete().eq("sku", sku).execute()
    return redirect(url_for("admin"))


@app.route("/admin/user/add", methods=["POST"])
def add_user():
    if not logged_in():
        return redirect(url_for("login"))
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "agent")
    if username and password:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        supabase.table("coc_users").insert({
            "username": username, "password_hash": pw_hash, "role": role
        }).execute()
    return redirect(url_for("admin"))


@app.route("/admin/user/delete/<username>", methods=["POST"])
def delete_user(username):
    if not logged_in():
        return redirect(url_for("login"))
    supabase.table("coc_users").delete().eq("username", username).execute()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=False)
