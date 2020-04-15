from flask_admin import helpers, expose
import flask_admin as admin
import flask_login as login
import os
from flask import Flask, url_for, redirect, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash

# from .form import LoginForm, RegistrationForm

from service import db



# Create customized index view class that handles login & registration
class MyAdminIndexView(admin.AdminIndexView):


    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        if request.method == "GET":
            return render_template("admin/login.html")

        username = request.form.get("username")
        password = request.form.get("password")

        if not all([username, password]):
            return render_template("admin/login.html", errmsg="参数缺失")
        try:
            from ...model.model import SuperUser
            user = SuperUser.query.filter(SuperUser.name == username).first()
        except Exception as e:
            print(e)
            return render_template("admin/login.html", errmsg="用户信息查询失败")
        if not user:
            return render_template("admin/login.html", errmsg="用户不存在")
        if not user.check_poassword(password):
            return render_template("admin/login.html", errmsg="密码错误")

        login.login_user(user)

        if login.current_user.is_authenticated:
            next = request.args.get("next", None)
            if next is not None:
                return redirect(next)
            return redirect(url_for('.index'))


    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            from .model import SuperUser
            user = SuperUser()

            form.populate_obj(user)
            # we hash the users password to avoid saving it as plaintext in the db,
            # remove to use plain text:
            user.password = generate_password_hash(form.password.data)

            db.session.add(user)
            db.session.commit()

            login.login_user(user)
            return redirect(url_for('.index'))
        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))