from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post

from db.utils import row_to_dict, rows_to_list
from middlewares import auth_required

SORT_BY = ["id", "reads", "likes", "popularity"]
DIRECTION = ["asc", "desc"]
DELIMITER = ","


@api.post("/posts")
@auth_required
def posts():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    data = request.get_json(force=True)
    text = data.get("text", None)
    tags = data.get("tags", None)
    if text is None:
        return jsonify({"error": "Must provide text for the new post"}), 400

    # Create new post
    post_values = {"text": text}
    if tags:
        post_values["tags"] = tags

    post = Post(**post_values)
    db.session.add(post)
    db.session.commit()

    user_post = UserPost(user_id=user.id, post_id=post.id)
    db.session.add(user_post)
    db.session.commit()

    return row_to_dict(post), 200


@api.get("/posts")
@auth_required
def fetch():
    # validate user
    user = g.get("user")
    if user is None:
        return abort(401)

    # get query params
    ids_str = request.args.get("authorIds")
    sort_by = request.args.get("sortBy", "id")
    dir = request.args.get("direction", "asc")

    # reverse sort boolean
    dir_reversed = dir == "desc"

    # check for invalid parameters
    if ids_str is None:
        return jsonify({"error": "authorIds are required"}), 400
    if sort_by not in SORT_BY:
        return jsonify({"error": "Invalid sortBy value"}), 400
    if dir not in DIRECTION:
        return jsonify({"error": "Invalid direction value"}), 400

    # add all rows to a set for uniqueness
    rows = set()
    ids = ids_str.split(DELIMITER)
    for id in ids:
        rows.update(Post.get_posts_by_user_id(id))

    # convert to list for ordering
    results = rows_to_list(rows)
    results.sort(key=lambda k: k[sort_by], reverse=dir_reversed)

    return jsonify({"posts": results}), 200


@api.patch("/posts/<int:postId>")
@auth_required
def update(postId):
    # check if logged in
    user = g.get("user")
    if user is None:
        return abort(401)

    # validate if post exists
    post = Post.query.get(postId)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    # find all authors of post
    user_posts = UserPost.query.filter(UserPost.post_id == postId).all()

    # validate user
    if not any([x.user_id == user.id for x in user_posts]):
        return jsonify({"error": "User is not author of this post"}), 403

    # get updated properties
    data = request.get_json()
    author_ids = data.get("authorIds", None)
    tags = data.get("tags", None)
    text = data.get("text", None)

    # check for invalid parameters
    if text is not None and not isinstance(text, str):
        return jsonify({"error": "text must be a string"}), 400
    if tags is not None and not (
        isinstance(tags, list) and all(isinstance(tag, str) for tag in tags)
    ):
        return jsonify({"error": "tags must be an array of strings"}), 400
    if author_ids is not None and not (
        isinstance(author_ids, list) and all(isinstance(id, int) for id in author_ids)
    ):
        return jsonify({"error": "authorIds must be an array of author ids"}), 400

    # update post with valid json data
    if tags is not None:
        post.tags = tags
    if text is not None:
        post.text = text

    # check if authors changed
    if author_ids is not None:
        # delete old and add new authors
        UserPost.query.filter(UserPost.post_id == postId).delete()
        for author_id in author_ids:
            user_post = UserPost(user_id=author_id, post_id=post.id)
            db.session.add(user_post)
    else:
        # create array of existing author ids
        author_ids = []
        for user_post in user_posts:
            author_ids.append(user_post.user_id)

    db.session.commit()
    result = row_to_dict(post)
    result["authorIds"] = author_ids
    return jsonify({"post": result}), 200
