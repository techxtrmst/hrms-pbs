from rest_framework import serializers
from .models import Employee
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "company",
            "manager",
            "designation",
            "department",
            "date_of_joining",
        ]
        read_only_fields = ["company", "user"]

    def create(self, validated_data):
        # API creation logic would need to handle nested user creation explicitly
        # For now, we assume simple employee update via API or sophisticated create logic
        return super().create(validated_data)
