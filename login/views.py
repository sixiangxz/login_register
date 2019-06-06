from django.shortcuts import render
from django.conf import settings
from django.shortcuts import redirect
from . import forms
from . import models
import datetime
import hashlib
# Create your views here.


def has_code(s, salt='hello_blog'):
    h = hashlib.sha384()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def make_confirm_str(user):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code = has_code(user.name, now)
    models.ConfirmStr.objects.create(code=code, user=user)
    return code


def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives

    subject = '来自www.xxx.com的注册确认邮件'

    text_content = '''感谢注册www.xxx.com,
                    如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'''

    html_content = '''
                    <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.liujiangblog.com</a>，\
                    这里是......</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>
                    '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)

    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def index(request):

    # 没登录不允许前往主页
    if not request.session.get('is_login', None):
        print('jaja')
        return redirect('/login/')
    print("gg")
    return render(request, 'login/index.html')


def login(request):
    # 不允许重复登录
    if request.session.get('is_login', None):
        return redirect('/index/')
    if request.method == 'POST':
        login_form = forms.UserForm(request.POST)
        message = '请检查填写的内容！'
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
            try:
                user = models.User.objects.get(name=username)
            except:
                message = '你输入的用户不存在！'
                return render(request, 'login/login.html', locals())
            if not user.has_confirmed:
                message = '该用户还未经过邮件确认！'
                return render(request, 'login/login.html', locals())
            if user.password == has_code(password):
                request.session['is_login'] = True
                request.session['username'] = user.name
                request.session['user_id'] = user.id
                return redirect('/index/')
            else:
                message = '你输入的密码不正确！'
                return render(request, 'login/login.html', locals())
        else:
            return render(request, 'login/login.html', locals())

    login_form = forms.UserForm()
    return render(request, 'login/login.html', locals())


def register(request):
    # 未登出，不允许注册
    if request.session.get('is_login', None):
        return redirect('/index/')
    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = "请检查你输入的内容！"
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            sex = register_form.cleaned_data.get('sex')

            if password1 != password2:
                message = '你两次输入的密码不同，请重新输入！'
                return render(request, 'login/register.html', locals())
            else:
                same_name_user = models.User.objects.filter(name=username)
                if same_name_user:
                    message = '存在相同的用户名，请重新输入！'
                    return render(request, 'login/register.html', locals())
                same_email_user = models.User.objects.filter(email=email)
                if same_email_user:
                    message = '存邮箱已注册，请重新输入！'
                    return render(request, 'login/register.html', locals())
                new_user = models.User()
                new_user.name = username
                new_user.password = has_code(password1)
                new_user.email = email
                new_user.sex = sex
                new_user.save()
                code = make_confirm_str(new_user)
                send_email(email, code)
                return redirect('/login/')

        else:
            return render(request, 'login/register.html', locals())
    register_form = forms.RegisterForm()
    return render(request, 'login/register.html', locals())


def logout(request):

    if request.session.get('is_login', None):
        # 清除所有的session，指定清除session需要
        # del request.session['is_login']
        request.session.flush()
        return redirect('/login/')
    return redirect('/login/')


def email_confirm(request):
    # 通过GET获得code值
    code = request.GET.get('code', None)
    message = ''
    try:
        # 防止伪造的code
        confirm = models.ConfirmStr.objects.get(code=code)
    except:
        message = '无效的确认邮件！'
        return render(request, 'login/confirm.html', locals())
    # 判断邮件是否超过验证期限
    c_time = confirm.c_time
    # now——(2019, 5, 28, 17, 18, 45, 137713)
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '该邮件已经过期！请重新注册！'
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '感谢确认，请使用账户登录！'
        return render(request, 'login/confirm.html', locals())
