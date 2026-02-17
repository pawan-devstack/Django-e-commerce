from django.shortcuts import render,redirect
from .models import Product,Customer,Order,OrderItem
from django.db.models import Q
from django.contrib.auth.hashers import make_password,check_password

import razorpay
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
# Create your views here.

def home(req):
    products=Product.objects.all()

    query=req.GET.get('q')
    if query:
        products=products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query))

    price_filter=req.GET.get('price')
    if price_filter:
        if price_filter=='0-99':
            products=products.filter(price__gte=0,price__lte=99)
        elif price_filter=='100-499':
            products=products.filter(price__gte=100,price__lte=499)
        elif price_filter=='500-999':
            products=products.filter(price__gte=500,price__lte=999)
        elif price_filter=='1000-1999':
            products=products.filter(price__gte=1000,price__lte=1999)
        elif price_filter=='2000-4999':
            products=products.filter(price__gte=2000,price__lte=4999)
        elif price_filter=='5000plus':
            products=products.filter(price__gte=5000)
        
    category_filter=req.GET.get('category')
    if category_filter:
        products=products.filter(category=category_filter)
    
    sort_filter=req.GET.get('sort')
    if sort_filter:
        if sort_filter=='low':
            products=products.order_by('price')
        elif sort_filter=='high':
            products=products.order_by('-price')
    
    auth=req.session.get('auth')


    context={
        'products':products,
        'auth':auth,
        'price_filter':price_filter,
        'category_filter':category_filter,
        'sort_filter':sort_filter
    }

    return render(req,'home.html',context)

def signup(req):
    return render(req,'signup.html')

def login(req):
    return render(req,'login.html')

def register_data(req):
    if req.method=='POST':
        n=req.POST.get('name')
        e=req.POST.get('email')
        p=req.POST.get('password')
        cp=req.POST.get('confirm_password')

        if Customer.objects.filter(email=e).exists():
            return render(req,'signup.html',{'message':'this email already exists'})
        
        if p!=cp:
            return render(req,'signup.html',{'message':'password and confirm password not matched'})
        
        hashed_password=make_password(p)
        Customer.objects.create(name=n,email=e,password=hashed_password)
        return redirect('login')
    
def login_data(req):
    if req.method=='POST':
        e=req.POST.get('email')
        p=req.POST.get('password')
        
        if e=='admin@gmail.com' and p=='12345':
            req.session['auth']={
                'is_logged_in':True,
                'role':'admin',
                'name':'Admin',
                'email':e
           }
            return redirect('admin_dashboard')
        else:
            cust=Customer.objects.filter(email=e)
            if not cust.exists():
                return render(req,'signup.html',{'message':'first you need to register with this email'})
            
            c=cust.first()
            if not check_password(p,c.password):
                return render(req,'login.html',{'message':'You entered the wrong password'})
            
            req.session['auth']={
                'is_logged_in':True,
                'role':'customer',
                'name':c.name,
                'email':c.email,
                'user_id':c.id
            }
            return redirect('home')

def admin_dashboard(req):
    auth=req.session.get('auth')
    if not auth or auth.get('role')!='admin':
        return redirect('login')
    
    data={'name':auth['name'],'email':auth['email']}
    return render(req,'admin_dashboard.html',data)

def logout(req):
    req.session.flush()
    return redirect('home')

def add_product(req):
    if req.method=='POST':
        n=req.POST.get('name')
        p=req.POST.get('price')
        d=req.POST.get('description')
        i=req.FILES.get('image')
        c=req.POST.get('category')
        s=req.POST.get('stock')

        Product.objects.create(name=n,price=p,description=d,image=i,category=c,stock=s)
        return redirect('view_products')


    return render(req,'add_product.html')

def view_products(req):
    products=Product.objects.all()
    return render(req,'view_products.html',{'products':products})

def edit_product(req,id):
    product=Product.objects.get(id=id)
    
    if req.method=='POST':
        n=req.POST.get('name')
        p=req.POST.get('price')
        d=req.POST.get('description')
        s=req.POST.get('stock')
        c=req.POST.get('category')

        if req.FILES.get('image'):
          product.image = req.FILES.get('image')

        
        product.name=n
        product.price=p
        product.description=d
        product.stock=s
        product.category=c
        product.save()
        return redirect('view_products')

    return render(req,'edit_product.html',{'product':product})

def delete_product(req,id):
    product=Product.objects.get(id=id)
    product.delete()
    return redirect('view_products')

def view_users(req):
    users=Customer.objects.all()
    return render(req,'view_users.html',{'users':users})

def product_detail(req,id):
    product=Product.objects.get(id=id)
    return render(req,'product_detail.html',{'product':product})

def add_to_cart(req,id):
    product=Product.objects.get(id=id)

    if product.stock==0:
        return redirect('product_detail',id=id)
    
    cart=req.session.get('cart',{})

    if str(id) in cart:
        if cart[str(id)]['qty']<product.stock:
            cart[str(id)]['qty']=cart[str(id)]['qty']+1
            cart[str(id)]['item_total']=cart[str(id)]['qty']*cart[str(id)]['price']

    else:
        cart[str(id)]={
            'name':product.name,
            'price':int(product.price),
            'qty':1,
            'image':product.image.url,
            'item_total':int(product.price),
            'stock':product.stock
        }
    req.session['cart']=cart
    return redirect('cart')

def cart(req):
    cart=req.session.get('cart',{})
    total=0

    for item in cart.values():
        item['total_item']=item['qty']*item['price']
        total=total+item['total_item']

    req.session['cart']=cart
    return render(req,'cart.html',{'cart':cart,'total':total})

def cart_add(req, id):
    cart = req.session.get('cart', {})
    product = Product.objects.get(id=id)

    if str(id) in cart:
        if cart[str(id)]['qty'] < product.stock:
            cart[str(id)]['qty'] += 1
            cart[str(id)]['item_total'] = cart[str(id)]['qty'] * cart[str(id)]['price']

    req.session['cart'] = cart
    return redirect('cart')

def remove_cart(req,id):
    cart=req.session.get('cart',{})
    
    if str(id) in cart:
        cart[str(id)]['qty']=cart[str(id)]['qty']-1

        if cart[str(id)]['qty']<=0:
            del cart[str(id)]
        else:
            cart[str(id)]['item_total']=cart[str(id)]['qty']*cart[str(id)]['price']
    
    req.session['cart']=cart
    return redirect('cart')

def cart_delete(req,id):
    cart=req.session.get('cart',{})

    if str(id) in cart:
        del cart[str(id)]
    
    req.session['cart']=cart
    return redirect('cart')

def checkout(req):
    auth=req.session.get('auth')
    if not auth or auth.get('role')!='customer':
        return redirect('login')
    
    cart=req.session.get('cart')
    if not cart:
        return redirect('home')
    
    return render(req,'checkout.html')

def place_order(req):

    if req.method != 'POST':
        return redirect('home')

    auth = req.session.get('auth')
    if not auth or auth.get('role') != 'customer':
        return redirect('login')

    cart = req.session.get('cart')
    if not cart:
        return redirect('home')

    total = 0
    for key, item in cart.items():
        total += item['price'] * item['qty']

    order = Order.objects.create(
        user_id=auth['user_id'],
        total_amount=total,
        payment_method=req.POST.get('payment_method'),
        status="Paid"
    )

    for key, item in cart.items():
        product = Product.objects.get(id=key)

        if product.stock < item['qty']:
            return redirect('cart')

        product.stock -= item['qty']
        product.save()

        OrderItem.objects.create(
            order=order,
            product=product,
            price=product.price,
            qty=item['qty']
        )

    req.session['cart'] = {}

    return render(req, 'order_success.html', {'order': order})

def order_history(req):
    auth=req.session.get('auth')
    if not auth or auth.get('role')!="customer":
        return redirect('login')
    
    orders=Order.objects.filter(user_id=auth['user_id'])
    return render(req,'order_history.html',{'orders':orders})


@api_view(['POST'])
def create_order(request):

    auth = request.session.get('auth')
    if not auth:
        return Response({"error": "Login required"}, status=400)

    cart = request.session.get('cart')
    if not cart:
        return Response({"error": "Cart empty"}, status=400)

    total = 0
    for key, item in cart.items():
        total += item['price'] * item['qty']

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    payment = client.order.create({
        "amount": int(total) * 100,
        "currency": "INR",
        "payment_capture": 1
    })

    order = Order.objects.create(
        user_id=auth['user_id'],
        total_amount=total,
        payment_method="Razorpay",
        razorpay_order_id=payment["id"],
        status="Pending"
    )

    return Response({
        "order_id": payment["id"],
        "amount": payment["amount"],
        "key": settings.RAZORPAY_KEY_ID
    })


@api_view(['POST'])
def verify_payment(request):

    try:
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        client.utility.verify_payment_signature({
            'razorpay_order_id': request.data['razorpay_order_id'],
            'razorpay_payment_id': request.data['razorpay_payment_id'],
            'razorpay_signature': request.data['razorpay_signature']
        })

        order = Order.objects.get(
            razorpay_order_id=request.data['razorpay_order_id']
        )

        if order.status == "Paid":
            return Response({"status": "Already Paid"})

        order.razorpay_payment_id = request.data['razorpay_payment_id']
        order.razorpay_signature = request.data['razorpay_signature']
        order.status = "Paid"
        order.save()

        cart = request.session.get('cart', {})

        for key, item in cart.items():
            product = Product.objects.get(id=key)

            if product.stock < item['qty']:
                return Response({"error": "Insufficient stock"}, status=400)

            product.stock -= item['qty']
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price,
                qty=item['qty']
            )

        request.session['cart'] = {}

        return Response({"status": "Payment Successful"})

    except Exception as e:
        print("Payment Error:", e)
        return Response({"status": "Payment Failed"}, status=400)
