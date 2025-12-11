# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'vendors', VendorViewSet,basename="vendors")
router.register(r'customers', CustomerViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'products', ProductViewSet)
router.register(r'income', IncomeViewSet)
router.register(r'expenses', ExpenseViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'bank-accounts', BankAccountViewSet)
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
]