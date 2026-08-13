from django.urls import include, path

urlpatterns = [
    path('chat/', include('apps.chat.urls', namespace='chat')),
    path('', include('apps.notification.urls', namespace='notification')),
    # Domain APIs. Mobile storefront projections live under /api/v1/storefront/.
    path('category/', include('apps.category.urls.general_urls')),
    path('info/', include('apps.information.urls.general_urls')),
    path('region/', include('apps.region.urls.general_urls')),
    path('advertisements/', include('apps.advertise.urls.user')),
    path('user/comment/', include('apps.comment.urls')),

    # authenticated user endpoints
    path('user/market/', include('apps.market.urls.user_urls')),
    path('user/', include('apps.users.urls.user_urls')),
    path('discount/', include('apps.discount.urls')),
    path('sms/owner/', include('apps.sms.urls.owner')),
    path('sms/admin/', include('apps.sms.urls.admin')),
    path('reservation/owner/', include('apps.reserve.urls.owner')),
    path('reservation/user/', include('apps.reserve.urls.user')),
    path('user/inquiries/', include('apps.price_inquiry.urls.user')),
    path('user/affiliate/', include('apps.affiliate.urls.user')),
    path('wallet/', include('apps.wallet.urls')),
    path('user/referral/', include('apps.referral.urls.user')),
    path('user/payments/', include('apps.payment.urls.user')),
    path('user/order/', include('apps.cart.urls.user')),
    path('analytics/', include('apps.analytics.urls')),

    # owner endpoints
    path('owner/market/', include('apps.market.urls.owner_urls')),
    path('owner/product/', include('apps.product.urls.owner_urls')),
    path('owner/inquiries/', include('apps.price_inquiry.urls.owner')),
    path('owner/affiliate/', include('apps.affiliate.urls.owner')),
    path('owner/order/', include('apps.cart.urls.owner')),

    # admin / platform endpoints
    path('admin/markets/', include('apps.market.urls.admin_urls')),
    path('admin/referrals/', include('apps.referral.urls.admin')),
    path('admin/products/', include('apps.product.urls.admin_urls')),
]
