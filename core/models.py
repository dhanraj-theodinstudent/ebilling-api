# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

# 1. Custom User Manager to handle Mobile Number Login
class UserManager(BaseUserManager):
    def create_user(self, mobile_number, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError('The Mobile Number field must be set')
        user = self.model(mobile_number=mobile_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(mobile_number, password, **extra_fields)

class User(AbstractUser):
    username = None
    mobile_number = models.CharField(max_length=15, unique=True)
    #email, is_employee #is_vender
    
    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

# 2. Entity Models
class Vendor(models.Model):
    vendor_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    city = models.CharField(max_length=50)
    
    def __str__(self):
        return self.company_name

class Customer(models.Model):
    customer_name = models.CharField(max_length=100)
    shop_name = models.CharField(max_length=100, blank=True, null=True)
    mobile_number = models.CharField(max_length=15)
    city = models.CharField(max_length=50)

    def __str__(self):
        return self.customer_name

class Employee(models.Model):
    employee_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    city = models.CharField(max_length=50)
    salary_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.employee_name

# 3. Product Master
class Product(models.Model):
    product_name = models.CharField(max_length=100)
    category_name = models.CharField(max_length=50)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=0)
    stock_alert = models.IntegerField(default=10) # Minimum stock alert
    weight = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.product_name

# 4. Financial Masters
class BankAccount(models.Model):
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=20)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2)
    initial_amount = models.DecimalField(max_digits=12, decimal_places=2)

class Income(models.Model):
    name = models.CharField(max_length=100) # Source of income
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=50) # Cash/Online
    transaction_id = models.CharField(max_length=100, blank=True)

class Expense(models.Model):
    name = models.CharField(max_length=100) # Expense reason
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True)
    # Optional link to employee for salary payments
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)

# 5. Invoicing
class Invoice(models.Model):
    INVOICE_TYPES = (('SALE', 'Sale'), ('PURCHASE', 'Purchase'))
    invoice_type = models.CharField(max_length=10, choices=INVOICE_TYPES)
    
    # Links
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    @property
    def outstanding_amount(self):
        return self.total_amount - self.paid_amount

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)