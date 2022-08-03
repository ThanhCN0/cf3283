##  1. What database changes would be required to the starter code to allow for different roles for authors of a blog post? Imagine that we’d want to also be able to add custom roles and change the permission sets for certain roles on the fly without any code changes.   
The database would require two new tables, a Role and User_Role table.  
The Role table would have columns such as rolename, booleans for each different permission, and an id primary key.  
The User_Role table would represent a many-to-one relation between user and role (or many-to-many if users may have multiple roles). There would only be two foreign keys columns for role id and user id, with them forming the composite primary key.

## 2. How would you have to change the PATCH route given your answer above to handle roles?  
When the PATCH route validates if the logged-in user is an author of the post, I would add additional checks such as:
* allowing roles with permissions to update posts authored by other users
* checking if the author has permission to update their post.
