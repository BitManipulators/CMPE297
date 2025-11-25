import 'package:json_annotation/json_annotation.dart';

part 'user.g.dart';

@JsonSerializable()
class User {
  final String id;
  final String username;
  final String? email;
  final String? createdAt;
  final String? googleId;
  final String? picture;
  final String? lastLoginAt;

  User({
    required this.id,
    required this.username,
    this.email,
    this.createdAt,
    this.googleId,
    this.picture,
    this.lastLoginAt,
  });

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);

  Map<String, dynamic> toJson() => _$UserToJson(this);
}

