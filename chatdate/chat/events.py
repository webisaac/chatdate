from django_socketio import events, broadcast_channel
from django_socketio.utils import NoSocket
from django.contrib.auth import get_user_model
from .models import ReadyToChat
from relationship.models import Relationship

@events.on_message(channel="^[a-z0-9]{32}")
def handle_message(request, socket, context, message):
    """
    Handle all messages being sent between two people.
    """
    sent_by = message['sent_by']['hash']
    sent_to = message['sent_to']['hash']

    relationship = Relationship.objects.get_or_make_relationship(sent_to, sent_by)
    relationship.process_message(message['payload']['chat'], sent_by=sent_by)
    info_for_sent_by, info_for_sent_to, info_for_both = relationship.get_changes()

    sent_to_package = message
    sent_to_package['payload'].update(info_for_sent_to)
    sent_to_package['payload'].update(info_for_both)

    sent_by_package = message
    sent_by_package['payload'].update(info_for_sent_by)
    sent_by_package['payload'].update(info_for_both)

    broadcast_channel(sent_to_package, sent_to)
    broadcast_channel(sent_by_package, sent_by)

@events.on_subscribe(channel="^[a-z0-9]{32}")
def handle_connect(request, socket, context, channel):
    context['hash'] = channel
    User = get_user_model()
    user = User.objects.get(hash=channel)
    new_user = {'new_user': user.to_json()}
    online_and_nearby = []
    for nearby_user in user.local_users(online=True):
        # notify all neraby users that you have arrived.
        try:
            broadcast_channel(new_user, nearby_user.hash)
        except NoSocket:
            pass #ignore users who are not online
        online_and_nearby.append(nearby_user.to_json())

    broadcast_channel({'online_and_nearby': online_and_nearby}, channel) 
    ReadyToChat.objects.set_ready(channel)


@events.on_finish(channel="^[a-z0-9]{32}")
def handle_disconnect(request, socket, context):
    """
    When a user disconnects from the site, this event is fired.
    """
    hash = context['hash']
    ReadyToChat.objects.filter(user__hash=hash).delete()
    User = get_user_model()
    user = User.objects.get(hash=hash)
    remove_user = {'remove_user': user.to_json()}
    for nearby_user in user.local_users(online=True):
        # notify all neraby users that you have left
        try:
            broadcast_channel(remove_user, nearby_user.hash)
        except NoSocket:
            pass #ignore users who are not online