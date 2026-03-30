from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from authentication.models import MovingCompanyProfile, Role
from .models import MovingBooking, MovingCompanyReview
from .serializers import MovingBookingSerializer, MovingCompanyReviewSerializer, MovingCompanyListSerializer

# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def _is_moving_company(user):
    return user.role and user.role.name == Role.MOVING_COMPANY


def _company_owns_booking(user, booking):
    return booking.company.user == user


# ---------------------------------------------------------------------------
# Company directory
# ---------------------------------------------------------------------------

@extend_schema(methods=['GET'], summary="List active moving companies")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def company_list(request):
    companies = MovingCompanyProfile.objects.filter(is_active=True).select_related('user')
    serializer = MovingCompanyListSerializer(companies, many=True)
    return Response(serializer.data)


@extend_schema(methods=['GET'], summary="Get moving company detail")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def company_detail(request, pk):
    try:
        company = MovingCompanyProfile.objects.select_related('user').get(pk=pk)
    except MovingCompanyProfile.DoesNotExist:
        return Response({'error': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = MovingCompanyListSerializer(company)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="List own moving bookings",
)
@extend_schema(
    methods=['POST'],
    summary="Create a moving booking",
    examples=[
        OpenApiExample(
            "Create booking",
            request_only=True,
            value={
                "company": 1,
                "moving_date": "2026-04-15",
                "moving_time": "08:00:00",
                "pickup_address": "45 Old Town Road, Nairobi",
                "delivery_address": "12 New Estate, Westlands",
                "notes": "Fragile items — please handle with care",
            },
        )
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def booking_list(request):
    if request.method == 'GET':
        if _is_moving_company(request.user):
            try:
                profile = request.user.moving_company_profile
            except MovingCompanyProfile.DoesNotExist:
                return Response([], status=status.HTTP_200_OK)
            bookings = MovingBooking.objects.filter(company=profile).select_related('customer', 'company__user')
        else:
            bookings = MovingBooking.objects.filter(customer=request.user).select_related('customer', 'company__user')
        serializer = MovingBookingSerializer(bookings, many=True)
        return Response(serializer.data)

    # POST — any auth user can book (except moving companies booking themselves)
    serializer = MovingBookingSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(customer=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=['GET'],
    summary="Get booking detail",
)
@extend_schema(
    methods=['PUT'],
    summary="Update booking status",
    examples=[
        OpenApiExample(
            "Confirm booking",
            request_only=True,
            value={"status": "confirmed", "estimated_price": "8500.00"},
        ),
        OpenApiExample(
            "Cancel booking",
            request_only=True,
            value={"status": "cancelled"},
        ),
    ],
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    try:
        booking = MovingBooking.objects.select_related('customer', 'company__user').get(pk=pk)
    except MovingBooking.DoesNotExist:
        return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_customer = booking.customer == request.user
    is_company = _company_owns_booking(request.user, booking)
    is_admin = request.user.is_staff

    if not (is_customer or is_company or is_admin):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(MovingBookingSerializer(booking).data)

    # PUT — validate status transition
    new_status = request.data.get('status')
    if new_status:
        error = _validate_booking_status_transition(booking.status, new_status, is_customer, is_company)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

    serializer = MovingBookingSerializer(booking, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _validate_booking_status_transition(current, new, is_customer, is_company):
    valid_company = {
        MovingBooking.STATUS_PENDING: [MovingBooking.STATUS_CONFIRMED, MovingBooking.STATUS_CANCELLED],
        MovingBooking.STATUS_CONFIRMED: [MovingBooking.STATUS_IN_PROGRESS, MovingBooking.STATUS_CANCELLED],
        MovingBooking.STATUS_IN_PROGRESS: [MovingBooking.STATUS_COMPLETED],
    }
    valid_customer = {
        MovingBooking.STATUS_PENDING: [MovingBooking.STATUS_CANCELLED],
        MovingBooking.STATUS_CONFIRMED: [MovingBooking.STATUS_CANCELLED],
    }
    if is_company:
        allowed = valid_company.get(current, [])
    elif is_customer:
        allowed = valid_customer.get(current, [])
    else:
        return "Permission denied."
    if new not in allowed:
        return f"Cannot transition from '{current}' to '{new}'."
    return None


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="List reviews for a moving company",
)
@extend_schema(
    methods=['POST'],
    summary="Add a review for a moving company",
    examples=[
        OpenApiExample(
            "Add review",
            request_only=True,
            value={"rating": 4, "comment": "Professional and on time.", "booking": 1},
        )
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def review_list(request, company_pk):
    try:
        company = MovingCompanyProfile.objects.get(pk=company_pk)
    except MovingCompanyProfile.DoesNotExist:
        return Response({'error': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        reviews = MovingCompanyReview.objects.filter(company=company).select_related('reviewer')
        return Response(MovingCompanyReviewSerializer(reviews, many=True).data)

    serializer = MovingCompanyReviewSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save(reviewer=request.user, company=company)
        except IntegrityError:
            return Response({'detail': 'You have already reviewed this company.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a review")
@extend_schema(
    methods=['PATCH'],
    summary="Update own review",
    examples=[
        OpenApiExample("Update review", request_only=True, value={"rating": 5, "comment": "Even better on reflection."})
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete own review")
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def review_detail(request, company_pk, review_pk):
    try:
        review = MovingCompanyReview.objects.select_related('reviewer', 'company').get(
            pk=review_pk, company__pk=company_pk
        )
    except MovingCompanyReview.DoesNotExist:
        return Response({'error': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_reviewer = review.reviewer == request.user
    if not (is_reviewer or request.user.is_staff):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(MovingCompanyReviewSerializer(review).data)
    elif request.method == 'PATCH':
        serializer = MovingCompanyReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        review.delete()
        return Response({'deleted': True}, status=status.HTTP_204_NO_CONTENT)
