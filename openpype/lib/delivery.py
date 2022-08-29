"""Functions useful for delivery action or loader"""
import os
import shutil
import glob
import clique
import functools
import warnings


class DeliveryDeprecatedWarning(DeprecationWarning):
    pass


def deprecated(new_destination):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    func = None
    if callable(new_destination):
        func = new_destination
        new_destination = None

    def _decorator(decorated_func):
        if new_destination is None:
            warning_message = (
                " Please check content of deprecated function to figure out"
                " possible replacement."
            )
        else:
            warning_message = " Please replace your usage with '{}'.".format(
                new_destination
            )

        @functools.wraps(decorated_func)
        def wrapper(*args, **kwargs):
            warnings.simplefilter("always", DeliveryDeprecatedWarning)
            warnings.warn(
                (
                    "Call to deprecated function '{}'"
                    "\nFunction was moved or removed.{}"
                ).format(decorated_func.__name__, warning_message),
                category=DeliveryDeprecatedWarning,
                stacklevel=4
            )
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


@deprecated("openpype.lib.path_tools.collect_frames")
def collect_frames(files):
    """Returns dict of source path and its frame, if from sequence

    Uses clique as most precise solution, used when anatomy template that
    created files is not known.

    Assumption is that frames are separated by '.', negative frames are not
    allowed.

    Args:
        files(list) or (set with single value): list of source paths

    Returns:
        (dict): {'/asset/subset_v001.0001.png': '0001', ....}

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from .path_tools import collect_frames

    return collect_frames(files)


@deprecated("openpype.lib.path_tools.format_file_size")
def sizeof_fmt(num, suffix=None):
    """Returns formatted string with size in appropriate unit

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from .path_tools import format_file_size
    return format_file_size(num, suffix)


@deprecated("openpype.pipeline.load.get_representation_path_with_anatomy")
def path_from_representation(representation, anatomy):
    """Get representation path using representation document and anatomy.

    Args:
        representation (Dict[str, Any]): Representation document.
        anatomy (Anatomy): Project anatomy.

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.load import get_representation_path_with_anatomy

    return get_representation_path_with_anatomy(representation, anatomy)


def copy_file(src_path, dst_path):
    """Hardlink file if possible(to save space), copy if not"""
    from openpype.lib import create_hard_link  # safer importing

    if os.path.exists(dst_path):
        return
    try:
        create_hard_link(
            src_path,
            dst_path
        )
    except OSError:
        shutil.copyfile(src_path, dst_path)


@deprecated("openpype.pipeline.delivery.get_format_dict")
def get_format_dict(anatomy, location_path):
    """Returns replaced root values from user provider value.

    Args:
        anatomy (Anatomy)
        location_path (str): user provided value

    Returns:
        (dict): prepared for formatting of a template

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.delivery import get_format_dict

    return get_format_dict(anatomy, location_path)


@deprecated("openpype.pipeline.delivery.check_destination_path")
def check_destination_path(repre_id,
                           anatomy, anatomy_data,
                           datetime_data, template_name):
    """ Try to create destination path based on 'template_name'.

    In the case that path cannot be filled, template contains unmatched
    keys, provide error message to filter out repre later.

    Args:
        anatomy (Anatomy)
        anatomy_data (dict): context to fill anatomy
        datetime_data (dict): values with actual date
        template_name (str): to pick correct delivery template

    Returns:
        (collections.defauldict): {"TYPE_OF_ERROR":"ERROR_DETAIL"}

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.delivery import check_destination_path

    return check_destination_path(
        repre_id,
        anatomy,
        anatomy_data,
        datetime_data,
        template_name
    )


def process_single_file(
    src_path, repre, anatomy, template_name, anatomy_data, format_dict,
    report_items, log
):
    """Copy single file to calculated path based on template

        Args:
            src_path(str): path of source representation file
            _repre (dict): full repre, used only in process_sequence, here only
                as to share same signature
            anatomy (Anatomy)
            template_name (string): user selected delivery template name
            anatomy_data (dict): data from repre to fill anatomy with
            format_dict (dict): root dictionary with names and values
            report_items (collections.defaultdict): to return error messages
            log (Logger): for log printing
        Returns:
            (collections.defaultdict , int)
    """
    # Make sure path is valid for all platforms
    src_path = os.path.normpath(src_path.replace("\\", "/"))

    if not os.path.exists(src_path):
        msg = "{} doesn't exist for {}".format(src_path, repre["_id"])
        report_items["Source file was not found"].append(msg)
        return report_items, 0

    anatomy_filled = anatomy.format(anatomy_data)
    if format_dict:
        template_result = anatomy_filled["delivery"][template_name]
        delivery_path = template_result.rootless.format(**format_dict)
    else:
        delivery_path = anatomy_filled["delivery"][template_name]

    # Backwards compatibility when extension contained `.`
    delivery_path = delivery_path.replace("..", ".")
    # Make sure path is valid for all platforms
    delivery_path = os.path.normpath(delivery_path.replace("\\", "/"))

    delivery_folder = os.path.dirname(delivery_path)
    if not os.path.exists(delivery_folder):
        os.makedirs(delivery_folder)

    log.debug("Copying single: {} -> {}".format(src_path, delivery_path))
    copy_file(src_path, delivery_path)

    return report_items, 1


def process_sequence(
    src_path, repre, anatomy, template_name, anatomy_data, format_dict,
    report_items, log
):
    """ For Pype2(mainly - works in 3 too) where representation might not
        contain files.

        Uses listing physical files (not 'files' on repre as a)might not be
         present, b)might not be reliable for representation and copying them.

         TODO Should be refactored when files are sufficient to drive all
         representations.

        Args:
            src_path(str): path of source representation file
            repre (dict): full representation
            anatomy (Anatomy)
            template_name (string): user selected delivery template name
            anatomy_data (dict): data from repre to fill anatomy with
            format_dict (dict): root dictionary with names and values
            report_items (collections.defaultdict): to return error messages
            log (Logger): for log printing
        Returns:
            (collections.defaultdict , int)
    """
    src_path = os.path.normpath(src_path.replace("\\", "/"))

    def hash_path_exist(myPath):
        res = myPath.replace('#', '*')
        glob_search_results = glob.glob(res)
        if len(glob_search_results) > 0:
            return True
        return False

    if not hash_path_exist(src_path):
        msg = "{} doesn't exist for {}".format(src_path,
                                               repre["_id"])
        report_items["Source file was not found"].append(msg)
        return report_items, 0

    delivery_templates = anatomy.templates.get("delivery") or {}
    delivery_template = delivery_templates.get(template_name)
    if delivery_template is None:
        msg = (
            "Delivery template \"{}\" in anatomy of project \"{}\""
            " was not found"
        ).format(template_name, anatomy.project_name)
        report_items[""].append(msg)
        return report_items, 0

    # Check if 'frame' key is available in template which is required
    #   for sequence delivery
    if "{frame" not in delivery_template:
        msg = (
            "Delivery template \"{}\" in anatomy of project \"{}\""
            "does not contain '{{frame}}' key to fill. Delivery of sequence"
            " can't be processed."
        ).format(template_name, anatomy.project_name)
        report_items[""].append(msg)
        return report_items, 0

    dir_path, file_name = os.path.split(str(src_path))

    context = repre["context"]
    ext = context.get("ext", context.get("representation"))

    if not ext:
        msg = "Source extension not found, cannot find collection"
        report_items[msg].append(src_path)
        log.warning("{} <{}>".format(msg, context))
        return report_items, 0

    ext = "." + ext
    # context.representation could be .psd
    ext = ext.replace("..", ".")

    src_collections, remainder = clique.assemble(os.listdir(dir_path))
    src_collection = None
    for col in src_collections:
        if col.tail != ext:
            continue

        src_collection = col
        break

    if src_collection is None:
        msg = "Source collection of files was not found"
        report_items[msg].append(src_path)
        log.warning("{} <{}>".format(msg, src_path))
        return report_items, 0

    frame_indicator = "@####@"

    anatomy_data["frame"] = frame_indicator
    anatomy_filled = anatomy.format(anatomy_data)

    if format_dict:
        template_result = anatomy_filled["delivery"][template_name]
        delivery_path = template_result.rootless.format(**format_dict)
    else:
        delivery_path = anatomy_filled["delivery"][template_name]

    delivery_path = os.path.normpath(delivery_path.replace("\\", "/"))
    delivery_folder = os.path.dirname(delivery_path)
    dst_head, dst_tail = delivery_path.split(frame_indicator)
    dst_padding = src_collection.padding
    dst_collection = clique.Collection(
        head=dst_head,
        tail=dst_tail,
        padding=dst_padding
    )

    if not os.path.exists(delivery_folder):
        os.makedirs(delivery_folder)

    src_head = src_collection.head
    src_tail = src_collection.tail
    uploaded = 0
    for index in src_collection.indexes:
        src_padding = src_collection.format("{padding}") % index
        src_file_name = "{}{}{}".format(src_head, src_padding, src_tail)
        src = os.path.normpath(
            os.path.join(dir_path, src_file_name)
        )

        dst_padding = dst_collection.format("{padding}") % index
        dst = "{}{}{}".format(dst_head, dst_padding, dst_tail)
        log.debug("Copying single: {} -> {}".format(src, dst))
        copy_file(src, dst)
        uploaded += 1

    return report_items, uploaded
