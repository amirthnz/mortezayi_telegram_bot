from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from shop.models import Product
from shop.forms import ProductForm, ProductImageForm

# List all products
def list_product(request):
    product_list = Product.objects.all()
    paginator = Paginator(product_list, 12)
    page_number = request.GET.get('page', 1)
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    return render(request, 'shop/product/list.html', {'products': products})

# Add product using form
def add_product(request):
    if request.method == 'POST':
        product_form  = ProductForm(request.POST, request.FILES)
        if product_form .is_valid():
            product = product_form .save()
            # Handle image uploads
            image_forms = [ProductImageForm(request.POST, request.FILES, prefix=str(i)) for i in range(5)]  # Limit to 5 uploads
            for form in image_forms:
                product_image = form.save(commit=False)
                product_image.product = product
                product_image.save()
            messages.success(request, 'محصول جدید افزوده شد')
            return redirect('shop:product_list')
    else:
        product_form  = ProductForm()
        image_forms = [ProductImageForm(prefix=str(i)) for i in range(5)]  # Limit to 5 uploads

    return render(request, 'shop/product/add.html', {'form': product_form, 'image_forms': image_forms, })

# Edit product using form
def edit_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()

            image_forms = [ProductImageForm(request.POST, request.FILES, prefix=str(i)) for i in range(5)]  # Limit to 5 uploads
            for form in image_forms:
                product_image = form.save(commit=False)
                product_image.product = product
                product_image.save()

            messages.success(request, 'محصول  با موفقیت ویرایش شد')
            return redirect('shop:product_list')

    else:
        form = ProductForm(instance=product)
        image_forms = [ProductImageForm(prefix=str(i)) for i in range(5)]  # Limit to 5 uploads

    return render(request, 'shop/product/edit.html', {'form': form, 'image_forms': image_forms,})

# Delete product
def delete_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    product.delete()
    return redirect('shop:product_list')