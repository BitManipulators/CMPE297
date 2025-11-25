// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

User _$UserFromJson(Map<String, dynamic> json) => User(
  id: json['id'] as String,
  username: json['username'] as String,
  email: json['email'] as String?,
  createdAt: json['createdAt'] as String?,
  googleId: json['googleId'] as String?,
  picture: json['picture'] as String?,
  lastLoginAt: json['lastLoginAt'] as String?,
);

Map<String, dynamic> _$UserToJson(User instance) => <String, dynamic>{
  'id': instance.id,
  'username': instance.username,
  'email': instance.email,
  'createdAt': instance.createdAt,
  'googleId': instance.googleId,
  'picture': instance.picture,
  'lastLoginAt': instance.lastLoginAt,
};
