# core/views.py

from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.db.models import Sum, Count, F
from django.contrib.auth import authenticate

from .models import *
from .serializers import *

# ==========================================
# 1. Authentication & User Management
# ==========================================

class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny] # Allow anyone to attempt login

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            # Authenticate using mobile_number and password
            user = authenticate(
                username=serializer.data['mobile_number'],
                password=serializer.data['password']
            )
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key, 
                    'user_id': user.id,
                    'mobile_number': user.mobile_number
                })
            return Response({'error': 'Invalid Credentials'}, status=400)
        return Response(serializer.errors, status=400)

class ChangePasswordView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.data['current_password']):
                return Response({'error': 'Wrong current password'}, status=400)
            
            user.set_password(serializer.data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=400)


# ==========================================
# 2. Dashboard
# ==========================================

class DashboardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Aggregating data for the dashboard cards
        total_income = Income.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        
        data = {
            'total_vendors': Vendor.objects.count(),
            'total_customers': Customer.objects.count(),
            'total_employees': Employee.objects.count(),
            'total_income': total_income,
            'total_expense': total_expense,
            'net_balance': total_income - total_expense,
            'total_invoices': Invoice.objects.count(),
            # Products where current quantity is less than or equal to the alert level
            'low_stock_products': Product.objects.filter(quantity__lte=F('stock_alert')).count()
        }
        return Response(data)


# ==========================================
# 3. Master Entities (Vendor, Customer, Employee)
# ==========================================

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    
    # Feature: Check outstanding amount for a specific vendor
    @action(detail=True, methods=['get'])
    def outstanding(self, request, pk=None):
        vendor = self.get_object()
        invoices = Invoice.objects.filter(vendor=vendor)
        # Summing up outstanding amounts from all invoices related to this vendor
        total_due = sum([inv.outstanding_amount for inv in invoices])
        return Response({'vendor': vendor.vendor_name, 'outstanding_amount': total_due})

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    # Feature: Check outstanding amount for a specific customer
    @action(detail=True, methods=['get'])
    def outstanding(self, request, pk=None):
        customer = self.get_object()
        invoices = Invoice.objects.filter(customer=customer)
        total_due = sum([inv.outstanding_amount for inv in invoices])
        return Response({'customer': customer.customer_name, 'outstanding_amount': total_due})

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


# ==========================================
# 4. Product Management
# ==========================================

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # Feature: Get list of products hitting low stock
    @action(detail=False, methods=['get'])
    def stock_alerts(self, request):
        low_stock = Product.objects.filter(quantity__lte=F('stock_alert'))
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)


# ==========================================
# 5. Financial Management (Income & Expense)
# ==========================================

class IncomeViewSet(viewsets.ModelViewSet):
    queryset = Income.objects.all()
    serializer_class = IncomeSerializer

    def perform_create(self, serializer):
        """
        Auto-calculate Previous Balance before saving new Income.
        Previous Balance = Total Income - Total Expense (Before this transaction)
        """
        total_income = Income.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        current_balance = total_income - total_expense
        
        serializer.save(previous_balance=current_balance)

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def perform_create(self, serializer):
        """
        Auto-calculate Previous Balance before saving new Expense.
        """
        total_income = Income.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        current_balance = total_income - total_expense
        
        serializer.save(previous_balance=current_balance)

    # Feature: Pay Employee Salary (creates Expense + links Employee)
    @action(detail=False, methods=['post'])
    def pay_salary(self, request):
        data = request.data
        employee_id = data.get('employee_id')
        amount = data.get('amount')
        
        if not employee_id or not amount:
            return Response({'error': 'employee_id and amount are required'}, status=400)

        try:
            employee = Employee.objects.get(id=employee_id)
            
            # --- Logic for Previous Balance Auto-calculation ---
            total_income = Income.objects.aggregate(Sum('amount'))['amount__sum'] or 0
            total_expense = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
            current_balance = total_income - total_expense
            # ---------------------------------------------------

            expense = Expense.objects.create(
                name=f"Salary for {employee.employee_name}",
                amount=amount,
                previous_balance=current_balance,
                payment_type="Salary",
                employee=employee
            )
            
            # Optional: If you track 'paid salary' on the employee model, update it here.
            # employee.salary_balance += float(amount)
            # employee.save()

            return Response(ExpenseSerializer(expense).data, status=201)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=404)


# ==========================================
# 6. Invoicing & Banking
# ==========================================

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    # Feature: Generate WhatsApp Share Link
    @action(detail=True, methods=['get'])
    def whatsapp_share(self, request, pk=None):
        invoice = self.get_object()
        
        # Determine mobile number based on customer/vendor
        mobile = ""
        recipient_name = ""
        if invoice.customer:
             mobile = invoice.customer.mobile_number
             recipient_name = invoice.customer.customer_name
        elif invoice.vendor:
             mobile = invoice.vendor.mobile_number
             recipient_name = invoice.vendor.vendor_name
             
        # Create a summary message
        details = (
            f"Hello {recipient_name},\n"
            f"Here is your Invoice #{invoice.id}\n"
            f"Date: {invoice.date}\n"
            f"Total Amount: {invoice.total_amount}\n"
            f"Please pay at your earliest convenience."
        )
        
        # URL Encode the message slightly (basic spaces to %20) for safety
        import urllib.parse
        encoded_details = urllib.parse.quote(details)

        # WhatsApp API URL format
        url = f"https://wa.me/{mobile}?text={encoded_details}"
        
        return Response({'whatsapp_url': url})

class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer