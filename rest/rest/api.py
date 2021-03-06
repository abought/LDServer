from flask import current_app, Blueprint, request, jsonify, make_response, abort
from flask_cors import CORS
from webargs.flaskparser import parser
from webargs import fields
from model import Reference, File, Sample
from ld.pywrapper import LDServer, LDQueryResult, StringVec, correlation
import time

API_VERSION = "1.0"

bp = Blueprint('api', __name__)

CORS(bp)

def validate_query(value):
    if 'start' in value and 'stop' in value:
        if value['stop'] <= value['start']:
            return False
    return True

def build_link_next(args, result):
    if result.has_next():
        link_next = request.base_url + '?' + '&'.join(('{}={}'.format(arg, value) for arg, value in request.args.iteritems(True) if arg != 'last'))
        link_next += '&last={}'.format(result.get_last())
        return link_next
    return None

@bp.route('/correlations', methods = ['GET'])
def get_correlations():
    correlations = [
        { 'name': 'r', 'label': 'r', 'description': '', 'type': 'LD' },
        { 'name': 'rsquare', 'label': 'r^2', 'description': '', 'type': 'LD' },
        { 'name': 'covariance', 'label': 'cov', 'description': '', 'type': 'Covariance' }
    ]
    return make_response(jsonify(correlations), 200)

@bp.route('/references', methods = ['GET'])
def get_references():
    references = []
    for reference in Reference.query.all():
        references.append({'name': reference.name, 'description': reference.description, 'genome build': reference.genome_build, 'populations': list(set([s.subset for s in reference.samples]))})
    return make_response(jsonify(references), 200)

@bp.route('/references/<reference_name>', methods = ['GET'])
def get_reference_info(reference_name):
    reference = Reference.query.filter_by(name = reference_name).first()
    if reference:
        response = { 'name': reference.name, 'description': reference.description, 'genome build': reference.genome_build, 'populations': list(set([s.subset for s in reference.samples])) }
        return make_response(jsonify(response), 200)
    abort(404)

@bp.route('/references/<reference_name>/populations', methods = ['GET'])
def get_populations(reference_name):
    reference = Reference.query.filter_by(name = reference_name).first()
    if reference:
        populations = list(set([s.subset for s in reference.samples]))
        return make_response(jsonify(populations), 200)
    abort(404)

@bp.route('/references/<reference_name>/populations/<population_name>', methods = ['GET'])
def get_population_info(reference_name, population_name):
    reference = Reference.query.filter_by(name = reference_name).first()
    if reference is not None:
        samples = Sample.query.with_parent(reference).filter_by(subset = population_name).all()
        if samples:
            response = { 'name': population_name, 'size': len(samples) }
            return make_response(jsonify(response), 200)
    abort(404)

@bp.route('/references/<reference_name>/populations/<population_name>/regions', methods = ['GET'])
def get_region_ld(reference_name, population_name):
    arguments = {
        'chrom': fields.Str(required = True, validate = lambda x: len(x) > 0),
        'start': fields.Int(required = True, validate = lambda x: x >= 0),
        'stop': fields.Int(required = True, validate = lambda x: x > 0),
        'correlation': fields.Str(required = True, validate = lambda x: x in ['r', 'rsquare']),
        'limit': fields.Int(required = False, validate = lambda x: x > 0, missing = current_app.config['API_MAX_PAGE_SIZE']),
        'last': fields.Str(required = False, validate = lambda x: len(x) > 0)
    }
    args = parser.parse(arguments, validate = validate_query)
    if args['limit'] > current_app.config['API_MAX_PAGE_SIZE']:
        args['limit'] = current_app.config['API_MAX_PAGE_SIZE']
    if args['correlation'] == 'r':
        correlation_type = correlation.ld_r
    elif args['correlation'] == 'rsquare':
        correlation_type = correlation.ld_rsquare
    else:
        abort(404)
    reference = Reference.query.filter_by(name = reference_name).first()
    if reference is None:
        abort(404)
    samples = Sample.query.with_parent(reference).filter_by(subset = population_name).all()
    if not samples:
        abort(404)
    files = File.query.with_parent(reference).all()
    if not files:
        abort(404)
    #start = time.time()
    ldserver = LDServer(current_app.config['SEGMENT_SIZE_BP'])
    #end = time.time()
    #print "Created LD server in {} seconds.".format("%0.4f" % (end - start))
    #start = time.time()
    for file in files:
        ldserver.set_file(str(file.path))
    #end = time.time()
    #print "Files initialized in {} seconds.".format("%0.4f" % (end - start))
    if 'last' in args:
        result = LDQueryResult(args['limit'], str(args['last']))
    else:
        result = LDQueryResult(args['limit'])
    if population_name != 'ALL':
        s = StringVec()
        s.extend(str(sample.sample) for sample in samples)
        ldserver.set_samples(str(population_name), s)
    if current_app.config['CACHE_ENABLED']:
        ldserver.enable_cache(file.reference_id, current_app.config['CACHE_REDIS_HOSTNAME'], current_app.config['CACHE_REDIS_PORT'])
    #start = time.time()
    ldserver.compute_region_ld(str(args['chrom']), args['start'], args['stop'], correlation_type, result, str(population_name))
    #print "Computed results in {} seconds.".format("%0.4f" % (time.time() - start))
    #start = time.time()
    if current_app.config['PROXY_PASS']:
        base_url = '/'.join(x.strip('/') for x in [current_app.config['PROXY_PASS'], request.path])
    else:
        base_url = request.base_url
    base_url += '?' + '&'.join(('{}={}'.format(arg, value) for arg, value in request.args.iteritems(True) if arg != 'last'))
    j = result.get_json(str(base_url))
    #print "Jsonified result in {} seconds.".format("%0.4f" % (time.time() - start))
    #start = time.time()
    r = make_response(j, 200)
    r.mimetype = 'application/json'
    #print "Response created in {} seconds.".format("%0.4f" % (time.time() - start))
    return r


@bp.route('/references/<reference_name>/populations/<population_name>/variants', methods = ['GET'])
def get_variant_ld(reference_name, population_name):
    arguments = {
        'variant': fields.Str(required = True, validate = lambda x: len(x) > 0),
        'chrom': fields.Str(required = True, validate = lambda x: x > 0),
        'start': fields.Int(required = True, validate = lambda x: x >= 0),
        'stop': fields.Int(required = True, validate = lambda x: x > 0),
        'correlation': fields.Str(required = True, validate = lambda x: x in ['r', 'rsquare']),
        'limit': fields.Int(required = False, validate = lambda x: x > 0, missing = current_app.config['API_MAX_PAGE_SIZE']),
        'last': fields.Str(required = False, validate = lambda x: len(x) > 0)
    }
    args = parser.parse(arguments, validate = validate_query)
    if args['limit'] > current_app.config['API_MAX_PAGE_SIZE']:
        args['limit'] = current_app.config['API_MAX_PAGE_SIZE']
    if args['correlation'] == 'r':
        correlation_type = correlation.ld_r
    elif args['correlation'] == 'rsquare':
        correlation_type = correlation.ld_rsquare
    else:
        abort(404)
    reference = Reference.query.filter_by(name = reference_name).first()
    if reference is None:
        abort(404)
    samples = Sample.query.with_parent(reference).filter_by(subset = population_name).all()
    if not samples:
        abort(404)
    files = File.query.with_parent(reference).all()
    if not files:
        abort(404)
    ldserver = LDServer(current_app.config['SEGMENT_SIZE_BP'])
    for file in files:
        ldserver.set_file(str(file.path))
    if 'last' in args:
        result = LDQueryResult(args['limit'], str(args['last']))
    else:
        result = LDQueryResult(args['limit'])
    if population_name != 'ALL':
        s = StringVec()
        s.extend(str(sample.sample) for sample in samples)
        ldserver.set_samples(str(population_name), s)
    if current_app.config['CACHE_ENABLED']:
        ldserver.enable_cache(file.reference_id, current_app.config['CACHE_REDIS_HOSTNAME'], current_app.config['CACHE_REDIS_PORT'])
    start = time.time()
    ldserver.compute_variant_ld(str(args['variant']), str(args['chrom']), args['start'], args['stop'], correlation_type, result, str(population_name))
    print "Computed results in {} seconds.".format("%0.4f" % (time.time() - start))
    start = time.time()
    if current_app.config['PROXY_PASS']:
        base_url = '/'.join(x.strip('/') for x in [current_app.config['PROXY_PASS'], request.path])
    else:
        base_url = request.base_url
    base_url += '?' + '&'.join(('{}={}'.format(arg, value) for arg, value in request.args.iteritems(True) if arg != 'last'))
    j = result.get_json(str(base_url))
    print "Jsonified result in {} seconds.".format("%0.4f" % (time.time() - start))
    start = time.time()
    r = make_response(j, 200)
    r.mimetype = 'application/json'
    print "Response created in {} seconds.".format("%0.4f" % (time.time() - start))
    return r

# TODO: LD between arbitrary variants
# @bp.route('/<reference>/<population>/ld/cartesian', methods = ['GET'])
# def get_ld(reference, population):
#     arguments = {
#         'variants1': fields.DelimitedList(fields.Str()),
#         'variants2': fields.DelimitedList(fields.Str()),
#         'limit': fields.Int(required = False, validate = lambda x: x > 0, missing = API_MAX_PAGE_SIZE),
#         'last': fields.Function(deserialize = deserialize_query_last)
#     }
#     args = parser.parse(arguments, validate = validate_query)
#     dataset = datasets.get(reference, None)
#     if dataset is None:
#         abort(404)
#     if population not in dataset['Meta']['Samples']:
#         abort(404)
#     response = {}
#     pairs = PyLDServer.Pairs()
#     # compute ld
#     response['data'] = {
#         'chromosome1': [str(args['chrom'])] * len(pairs),
#         'variant1': [None] * len(pairs),
#         'position1': [None] * len(pairs),
#         'chromosome2': [str(args['chrom'])] * len(pairs),
#         'variant2': [None] * len(pairs),
#         'position2': [None] * len(pairs),
#         'r': [None] * len(pairs),
#         'rsquare': [None] * len(pairs)
#     }
#     for i, pair in enumerate(pairs):
#         response['data']['variant1'][i] = pair.name1
#         response['data']['position1'][i] = pair.position1
#         response['data']['variant2'][i] = pair.name2
#         response['data']['position2'][i] = pair.position2
#         response['data']['r'][i] = pair.r
#         response['data']['rsquare'][i] = pair.rsquare
#     response['next'] = None
#     return make_response(jsonify(response), 200)
