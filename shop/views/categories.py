from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from shop.models import Category
from shop.forms import CategoryForm


def category_list(request):
    categories = Category.objects.all()

    context = {
        'categories': categories
    }

    return render(request, 'shop/category/list.html', context)


def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'دسته بندی جدید افزوده شد')
            return redirect('shop:cat_list')


    form = CategoryForm()
    return render(request, 'shop/category/add.html', {'form': form})


# Edit category using form
def edit_category(request, pk):
    category = get_object_or_404(Category, id=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'دسته بندی با موفقیت ویرایش شد')
            return redirect('shop:cat_list')

    form = CategoryForm(instance=category)
    return render(request, 'shop/category/edit.html', {'form': form})


# Delete category
def delete_category(request, pk):
    category = get_object_or_404(Category, id=pk)
    category.delete()
    return redirect('shop:cat_list')