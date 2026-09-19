"""Independent crop/mark coordinates for editorial screenshots."""
import math


def box(value):
    if not isinstance(value,(list,tuple)) or len(value)!=4 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in value):
        raise ValueError('rectangle needs four finite coordinates')
    if value[2]<=value[0] or value[3]<=value[1]:raise ValueError('rectangle must have positive dimensions')
    return value


def envelope(boxes):
    checked=[box(b) for b in boxes]
    if not checked:raise ValueError('one small problem box per decisive point is required')
    return [min(b[0] for b in checked),min(b[1] for b in checked),max(b[2] for b in checked),max(b[3] for b in checked)]


def prepare_crop(crop, boxes, size):
    crop=list(box(crop));env=envelope(boxes)
    if len(size)!=2 or any(x<=0 for x in size):raise ValueError('invalid source image size')
    if crop[0]<0 or crop[1]<0 or crop[2]>size[0] or crop[3]>size[1]:raise ValueError('crop outside source page')
    if not (crop[0]<=env[0]<env[2]<=crop[2] and crop[1]<=env[1]<env[3]<=crop[3]):raise ValueError('problem boxes must stay inside the crop')
    limits=[]
    for axis in [0,1]:
        width=env[axis+2]-env[axis]
        if crop[axis+2]-crop[axis] >= 2*width:continue
        target=min(size[axis],math.ceil(2.5*width))
        start=max(0,min(math.floor((env[axis]+env[axis+2]-target)/2),size[axis]-target))
        crop[axis]=start;crop[axis+2]=start+target
        if target<2*width:limits.append('width' if axis==0 else 'height')
    return [int(round(x)) for x in crop],limits


def geometry_errors(evidence):
    try:
        crop=box(evidence.get('crop_box'));boxes=evidence.get('problem_boxes',[]);size=evidence.get('source_size',[])
        prepared,limits=prepare_crop(crop,boxes,size)
        errors=[]
        if prepared!=crop:errors.append('crop lacks 2x context; expand deficient axes without changing marks')
        if limits and not evidence.get('boundary_limitation'):errors.append('page boundary limitation must be recorded')
        if not evidence.get('context_anchor'):errors.append('locating context must identify an axis, room, header or node')
        if evidence.get('mark_color','#e32020').lower() not in {'#e32020','red','#ff0000'} and not evidence.get('color_authorization_ref'):errors.append('non-red mark requires user color instruction')
        return errors
    except (ValueError,TypeError,IndexError) as exc:return [str(exc)]
