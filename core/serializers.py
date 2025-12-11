# core/serializers.py
from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate

class UserLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField()
    password = serializers.CharField()

# core/serializers.py

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        # We include email/names as optional fields just in case you need them later
        fields = ['mobile_number', 'first_name', 'last_name', 'email', 'password', 'confirm_password']

    def validate(self, data):
        # 1. Check if passwords match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # 2. Check if mobile number already exists
        if User.objects.filter(mobile_number=data['mobile_number']).exists():
            raise serializers.ValidationError({"mobile_number": "This mobile number is already registered."})
        
        return data

    def create(self, validated_data):
        # Remove confirm_password before saving
        validated_data.pop('confirm_password')
        
        # specific logic to create user with encrypted password
        user = User.objects.create_user(
            mobile_number=validated_data['mobile_number'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        if len(data['new_password']) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters")
        return data

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'

class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.product_name')
    class Meta:
        model = InvoiceItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    outstanding = serializers.ReadOnlyField(source='outstanding_amount')
    customer_name = serializers.ReadOnlyField(source='customer.customer_name')
    vendor_name = serializers.ReadOnlyField(source='vendor.vendor_name')

    class Meta:
        model = Invoice
        fields = '__all__'

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(**validated_data)
        
        # Logic to update stock
        is_sale = invoice.invoice_type == 'SALE'
        
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
            product = item_data['product']
            if product:
                if is_sale:
                    product.quantity -= item_data['quantity']
                else: # Purchase
                    product.quantity += item_data['quantity']
                product.save()
                
        return invoice