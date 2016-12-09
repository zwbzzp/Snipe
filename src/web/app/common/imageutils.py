from .. import db
from flask.ext.login import current_user
from phoenix.cloud import image as OpenstackImageService
from ..models import User, Image

def list_of_image():
    image_list = []
    for image in OpenstackImageService.list_images():
        image_extra_specs = Image.query.filter_by(ref_id=image.id).first()
        if not image_extra_specs:
            image_extra_specs = Image()
            image_extra_specs.name = image.name
            image_extra_specs.ref_id = image.id
            user = User.query.filter_by(username='admin').first()
            image_extra_specs.owner_id = user.id
            image_extra_specs.visibility = 'public'
            db.session.add(image_extra_specs)
            db.session.commit()
        if not current_user.is_administrator():
            if image_extra_specs.visibility == "public" or image_extra_specs.owner_id == current_user.id:
                image_list.append(image)
        else:
            image_list.append(image)
    return image_list