from django.db.models.signals import (
    post_save, 
    pre_delete, 
    m2m_changed,
    post_delete
)
from .models import (
    Profile, 
    ChatMessage, 
    FriendRequest,
    Notification,
    Story,
    StoryNotification,
    StoryComment,
    Comment,
    Post,
    MiscNotification
    )
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from django.utils import timezone
from foo_backend.celery import app
from fcm_django.models import FCMDevice
# from .signal_registry import profile


from datetime import datetime, timedelta

User = get_user_model()





# Signals to delete the media associated with a model if an instance is deleted.
@receiver(pre_delete, sender = Profile)
def delete_user_media(sender, instance, **kwargs):
    if(instance.profile_pic):
        instance.profile_pic.delete(False)


@receiver(post_delete, sender = Story)
def delete_story_media(sender, instance, **kwargs):
    if(instance.file):
        instance.file.delete(False)


@receiver(post_delete, sender = Post)
def delete_post_media(sender, instance, **kwargs):
    if(instance.file):
        instance.file.delete(False)


@receiver(post_delete, sender = ChatMessage)
def delete_chat_media(sender, instance, **kwargs):
    if(instance.file):
        instance.file.delete(False)







# Signal to create a profile when a user object is created


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and (not instance.admin):
        print(instance.token)
        device = FCMDevice.objects.create(registration_id=instance.token,user=instance,type="android")
        device.save()
        profile = Profile.objects.create(user=instance)
        profile.save()


# @receiver(post_save, sender=FriendRequest)
# def send_request(sender, instance, created, **kwargs):
#     if created:
#         send_request_celery.delay(instance.id)
        # if instance.status == "pending":
        #     channel_layer = get_channel_layer()
        #     print(channel_layer)
        #     if instance.to_user.profile.online:
        #         print("hes online")
        #         # send_notif(instance.to_user.username)
        #         async_to_sync(channel_layer.group_send)(instance.to_user.username, {
        #             "type": "notification", 
        #             "username": instance.from_user.username, 
        #             'user_id': instance.from_user.id, 
        #             'dp':instance.from_user.profile.profile_pic.url,
        #             'id': instance.id,
        #             'time':instance.time_created,
  #             })

@app.task()      
def send_request_celery(id):
    instance = FriendRequest.objects.get(id=id)
    if instance.status == "pending":
            channel_layer = get_channel_layer()
            print(channel_layer)
            if instance.to_user.profile.online:
                print("hes online")
                # send_notif(instance.to_user.username)
                async_to_sync(channel_layer.group_send)(str(instance.to_user.uprn), {
                    "type": "notification", 
                    "username": instance.from_user.username_alias, 
                    'user_id': instance.from_user.id, 
                    'dp':instance.from_user.profile.profile_pic.url,
                    'id': instance.id,
                    'time':instance.time_created,
                    })

# @receiver(post_save, sender=Story)
def story_created_notif(sender, instance, created, **kwargs):
    if created:
        story_created_notif_celery.delay(instance.id)
        # friends_qs = instance.user.profile.friends.all()
        # channel_layer = get_channel_layer()
        # test=[]
        # for user in friends_qs:
        #     notification = StoryNotification.objects.create(story=instance,notif_type="story_add",to_user=user)
        #     notification.save()
        #     if user.profile.online:
        #         print(user.username)
        #         _dict = {
        #             'type':'story_add',
        #             'u':instance.user.username,
        #             'u_id':instance.user.id,
        #             's_id':instance.id,
        #             'url':instance.file.url,
        #             'n_id':notification.id,
        #             'time':instance.time_created.strftime("%Y-%m-%d %H:%M:%S"),
        #         }
        #         test.append(_dict)
        #         async_to_sync(channel_layer.group_send)(user.username,_dict)
        # print(test)



@app.task()
def story_created_notif_celery(id):
        instance = Story.objects.get(id=id)
        friends_qs = list(instance.user.profile.friends.all())
        friends_qs.insert(0, instance.user)
        channel_layer = get_channel_layer()
        test=[]
        for user in friends_qs:
            notification = StoryNotification.objects.create(story=instance,notif_type="story_add",to_user=user)
            notification.save()
            if user.profile.online:
                print(user.username)
                _dict = {
                    'type':'story_add',
                    'u':instance.user.username_alias,
                    'u_id':instance.user.id,
                    'dp':instance.user.profile.profile_pic.url if instance.user.profile.profile_pic else "",
                    's_id':instance.id,
                    'url':instance.file.url,
                    'caption':instance.caption,
                    'n_id':notification.id,
                    'time':instance.time_created.strftime("%Y-%m-%d %H:%M:%S"),
                }
                test.append(_dict)
                async_to_sync(channel_layer.group_send)(str(user.uprn),{'type':'general_down_send','content':_dict})
        #my_notif = StoryNotification.objects.create(story=instance , notif_type="story_add", to_user=instance.user)
        print(test)




@receiver(m2m_changed,sender=Story.views.through)
def story_viewed(sender, instance, **kwargs):
    if(kwargs['action']=='post_add'):
        print('post add')
        # channel_layer = get_channel_layer()
        user_id = kwargs['pk_set'].pop()
        story_viewed_celery.delay(instance.id, user_id)
        # user = User.objects.get(id=user_id)
        # time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        # notif = StoryNotification(notif_type="story_view",to_user=instance.user,from_user=user,story=instance,time_created=time)
        # notif.save()
        # if instance.user.profile.online:
        #     _dict = {
        #         'type':'story_view',
        #         'u':user.username,
        #         'id':instance.id,
        #         'n_id':notif.id,
        #         'time':time
        #     }
        #     async_to_sync(channel_layer.group_send)(instance.user.username,_dict)
    
    # pass


@app.task()
def story_viewed_celery(instance_id, id):
        instance = Story.objects.get(id=instance_id)
        channel_layer = get_channel_layer()
        user_id = id
        user = User.objects.get(id=user_id)

        time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        notif = StoryNotification(notif_type="story_view",to_user=instance.user,from_user=user,story=instance,time_created=time)
        notif.save()
        if instance.user.profile.online:
            _dict = {
                'type':'story_view',
                'u':user.username_alias,
                'dp':user.profile.profile_pic.url if user.profile.profile_pic else '',
                'id':instance.id,
                'n_id':notif.id,
                'time':time
            }
            async_to_sync(channel_layer.group_send)(str(instance.user.uprn),{'type':'general_down_send','content':_dict})



# @receiver(post_save,sender=StoryComment)
def story_comment(sender, instance, **kwargs):
    if(kwargs['created']==True):
        story_comment_celery.delay(instance.id)
        # channel_layer = get_channel_layer()
        # story = instance.story
        # user = story.user
        # time = timezone.now().strftime("%Y-%m-%d %H:%M:%S") 
        # if instance.story.user.profile.online:
        #     _dict = {
        #         'type':'story_comment',
        #         'u':instance.username,
        #         'comment':instance.comment,
        #         'c_id':instance.id,
        #         's_id':instance.story.id,
        #         'time':time
        #     }
        #     async_to_sync(channel_layer.group_send)(user.username,_dict)

@app.task()
def story_comment_celery(id):
        instance =StoryComment.objects.get(id=id)
        channel_layer = get_channel_layer()
        story = instance.story

        user = story.user
        time = timezone.now().strftime("%Y-%m-%d %H:%M:%S") 
        if instance.story.user.profile.online:
            _dict = {
                'type':'story_comment',
                'u':instance.user.username_alias,
                'dp':instance.user.profile.profile_pic.url if instance.user.profile.profile_pic else '',
                'comment':instance.comment,
                'c_id':instance.id,
                's_id':instance.story.id,
                'time':time
            }
            async_to_sync(channel_layer.group_send)(str(user.uprn),{'type':'general_down_send','content':_dict})    


#@receiver(pre_delete, sender=Story)
def story_deleted_notif(instance):
    story_deleted_notif_celery.delay(instance.user.id,instance.id)
    # friends_qs = instance.user.profile.friends.all()
    # channel_layer = get_channel_layer()
    # test=[]
    # for user in friends_qs:
    #     notification = StoryNotification.objects.create(storyId=instance.id,notif_type="story_delete",to_user=user,from_user=instance.user)
    #     notification.save()
    #     if user.profile.online:
    #         print(user.username)
    #         _dict = {
    #             'type':'story_delete',
    #             'u':instance.user.username,
    #             's_id':instance.id,
    #             'n_id':notification.id,
    #         }
    #         test.append(_dict)
    #         async_to_sync(channel_layer.group_send)(user.username,_dict)
    # print(test)

@app.task()
def story_deleted_notif_celery(user_id,story_id):
        _user = User.objects.get(id=user_id)
        friends_qs = _user.profile.friends.all()
        channel_layer = get_channel_layer()
        test=[]
        for user in friends_qs:
            notification = StoryNotification.objects.create(storyId=story_id,notif_type="story_delete",to_user=user,from_user=_user)
            notification.save()
            if user.profile.online:
                print(user.username)
                _dict = {
                    'type':'story_delete',
                    'u_id':_user.id,
                    's_id':story_id,
                    'n_id':notification.id,
                }
                test.append(_dict)
                async_to_sync(channel_layer.group_send)(str(user.uprn),{'type':'general_down_send','content':_dict})
        print(test)



@receiver(m2m_changed,sender=Comment.mentions.through)
def comment_mention(sender, instance, **kwargs):
    if(kwargs['action']=='post_add'):
        print('post add')
        # channel_layer = get_channel_layer()

        user_id = kwargs['pk_set'].pop()
        comment_mention_celery.delay(instance.id, user_id)
        # user = User.objects.get(id=user_id)
        # time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        # notif = MiscNotification(from_user=instance.user, to_user= user, time_created=time, post_id=instance.post.id)
        # notif.save()
        
        # if user.profile.online:
        #     _dict = {
        #         'type':'mention_notif',
        #         'u':instance.user.username,
        #         'id':instance.post.id,
        #         'n_id':notif.id,
        #         'time':time,
        #         'dp':instance.user.profile.profile_pic.url
        #     }
        #     async_to_sync(channel_layer.group_send)(user.username,_dict)


@app.task()
def comment_mention_celery(instance_id,id):
        instance = Comment.objects.get(id=instance_id)
        channel_layer = get_channel_layer()

        user_id = id
        user = User.objects.get(id=user_id)
        if (instance.user == user):
            return
        time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        notif = MiscNotification(from_user=instance.user, to_user= user, time_created=time, post_id=instance.post.id, type="mention")
        notif.save()
        
        
        if user.profile.online:
            _dict = {
                'type':'mention_notif',
                'u':instance.user.username_alias,
                'id':instance.post.id,
                'n_id':notif.id,
                'time':time,
                'dp':instance.user.profile.profile_pic.url
            }
            async_to_sync(channel_layer.group_send)(str(user.uprn),{'type':'general_down_send','content':_dict})


@app.task()
def tell_them_i_have_changed_my_dp(id):
    instance = User.objects.get(id=id)
    user_id = instance.id
    friends_qs = instance.profile.friends.all()
    channel_layer = get_channel_layer()
    for friend in friends_qs:
        notif = Notification(notif_to=friend,ref_id=str(user_id),notif_type="dp_notif")
        notif.save()
        if friend.profile.online:
            _dict = {
                'type':'dp_update',
                'id':user_id,
                'n_id':notif.id,
            }
            async_to_sync(channel_layer.group_send)(str(friend.uprn), {'type':'general_down_send','content':_dict})


@app.task(name="story_remover")
def delete_expired_stories():
    stories_qs = Story.objects.all()
    
    cur_time = datetime.now()
    for story in stories_qs:
        story_age = cur_time - story.time_created
        if(story_age >= timedelta(hours=1)):
           
            print(story)
            story.delete()
            

@app.task(name="disconnect signal")
def get_informers_list(id):
    _user = User.objects.get(id=id)
    final_list =[]
    channel_layer = get_channel_layer()
    offline_inform_qs = _user.profile.people_i_should_inform.all()
    for user in offline_inform_qs:
        # if user.profile.online:
            # final_list.append([
            # user.username,
            _dict= {   
                    'type':'online_status',
                    'u':_user.username,
                    's':'offline'
                }
           
            # ])
            async_to_sync(channel_layer.group_send)(str(user.uprn),{'type':'general_down_send','content':_dict})
            

@app.task()
def remove_me_from_others_lists(id):
    _user = User.objects.get(id=id)
    qs = _user.profile.people_i_peek.all()
    for user in qs:
        user.profile.people_i_should_inform.remove(_user)

@app.task()
def friend_request_accepted_notif_celery(frnd_req_id):
    frnd_req = FriendRequest.objects.get(id=frnd_req_id)
    channel_layer = get_channel_layer()
    new_friend = frnd_req.to_user
    to_user = frnd_req.from_user
    time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    frnd_req.time_created = time
    
    
    _dict = {
        'type':'frnd_req_acpt',
        'u':new_friend.username_alias,
        'id':new_friend.id,
        'notif_id':frnd_req.id,
        'time':time,
        'dp':new_friend.profile.profile_pic.url,
    }
    if to_user.profile.online:
        async_to_sync(channel_layer.group_send)(str(to_user.uprn), {'type':'general_down_send','content':_dict})


@receiver(m2m_changed,sender=Post.likes.through)
def friend_liked_notif(sender, instance, **kwargs):
    if(kwargs['action']=='post_add'):
        print('post add')
        # channel_layer = get_channel_layer()

        user_id = kwargs['pk_set'].pop()
        friend_like_notif_celery.delay(instance.id, user_id)


@app.task()
def friend_like_notif_celery(post_id, user_id):
    post = Post.objects.get(id=post_id)
    post_user = post.user
    channel_layer = get_channel_layer()
    liked_user = User.objects.get(id=user_id)
    if liked_user==post_user:
        return 
    time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    notif = MiscNotification.objects.create(from_user=liked_user,to_user=post_user,type="like",time_created=time, post_id=post_id)
    notif.save()
    if post_user.profile.online:
        _dict = {
            'type':'like_notif',
            'u':liked_user.username_alias,
            'id':post_id,
            'dp':liked_user.profile.profile_pic.url,
            'notif_id':notif.id,
            'time':time,
        }
        async_to_sync(channel_layer.group_send)(str(post_user.uprn),{'type':'general_down_send','content':_dict})


@app.task()
def send_anonymous_notif(id):
    user = User.objects.get(id=id)
    device = user.fcmdevice_set.first()
    device.send_message("Picza", "You may have new messages.")