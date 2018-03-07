# coding=utf-8

#     National Oceanic and Atmospheric Administration (NOAA)
#     Alaskan Fisheries Science Center (AFSC)
#     Resource Assessment and Conservation Engineering (RACE)
#     Midwater Assessment and Conservation Engineering (MACE)

#  THIS SOFTWARE AND ITS DOCUMENTATION ARE CONSIDERED TO BE IN THE PUBLIC DOMAIN
#  AND THUS ARE AVAILABLE FOR UNRESTRICTED PUBLIC USE. THEY ARE FURNISHED "AS IS."
#  THE AUTHORS, THE UNITED STATES GOVERNMENT, ITS INSTRUMENTALITIES, OFFICERS,
#  EMPLOYEES, AND AGENTS MAKE NO WARRANTY, EXPRESS OR IMPLIED, AS TO THE USEFULNESS
#  OF THE SOFTWARE AND DOCUMENTATION FOR ANY PURPOSE. THEY ASSUME NO RESPONSIBILITY
#  (1) FOR THE USE OF THE SOFTWARE AND DOCUMENTATION; OR (2) TO PROVIDE TECHNICAL
#  SUPPORT TO USERS.

'''

The processed_data class stores and manipulates 2d sample data arrays along
with 1d arrays that define the horizontal and vertical axes of that data.
The horizontal axis is defined as 'ping_time' and the vertical axis is 'range'
or 'depth'. Other data associated with the axes may be present. Most will
be associated with the ping_time axis like vessel GPS position or speed.

    properties:
        channel_id: a list of channel id's that are linked to this data

        frequency: The frequency, in Hz, of the data contained in the object

        data_type: Data_type is a string defining the type of sample data the
            object contains. Valid values are:
                'Sv', 'sv', 'Sp', 'sp', 'angles', 'electrical_angles', 'power'

        sample_thickness: a float defining the vertical extent of the samples
            in meters. It is calculated as thickness = sample interval(s) *
            sound speed(m/s) / 2.

        sample_offset: The number of samples this data

        range: An array of floats defining the ranges of the individual samples
            in the sample data array. Initially this is range relative to the
            transducer face but you can change this.

        depth: Depth is range relative to the surface.

        *Either* depth or range will be present.

        This class inherits the following attributes from sample_data:

            n_pings: n_pings stores the total number of pings in the object

            n_samples: the number of samples in the 2d sample array

            ping_time: An array of numpy datetime64 objects representing the times
                of the individual pings.

        The attribute name of the sample data depends on the type of data the object
        contains. If the data_type is 'Sv', the Sv sample data attribute name is 'Sv'.
        The sample data array is a numpy array indexed as [n_pings, n_samples]. To
        access the 100th ping, you would do something like:

            p_data.Sv[100,:]

            or, if the data_type is 'power'

            p_data.power[100,:]


'''
import numpy as np
from ..sample_data import sample_data
from echolab2.processing import mask


class processed_data(sample_data):
    '''

    '''

    def __init__(self, channel_id, frequency, data_type):

        super(processed_data, self).__init__()

        #  set the frequency, channel_id, and data type
        self.channel_id = list(channel_id)
        self.frequency = frequency
        self.data_type = data_type

        #  sample thickness is the vertical extent of the samples in meters
        #  it is calculated as thickness = sample interval(s) * sound speed(m/s) / 2
        self.sample_thickness = 0

        #  sample offset is the number of samples the first row of data are offset away from
        #  the transducer face.
        self.sample_offset = 0


    def replace(self, obj_to_insert, ping_number=None, ping_time=None,
               index_array=None):
        """
        replace inserts data without shifting the existing data resulting in the
        existing data being overwritten by the data in "obj_to_insert"

        Args:
            obj_to_insert: an instance of echolab2.processed_data that contains the
                data you are using as the replacement. obj_to_insert's sample data
                will be vertically interpolated to the vertical axis of this object.

            ping_number: The ping number specifying the first ping to replace

            ping_time: The ping time specifying the first ping to replace

            index_array: A numpy array containing the indices of the pings you
                want to replace. Unlike when using a ping number or ping time,
                the pings do not have to be consecutive but the number of "pings"
                in the obj_to_insert must be the same as the number of elements
                in your index_array. When this keyword is present, the ping_number
                and ping_time keywords are ignored.

        You must specify a ping number, ping time or provide an index array.

        Replace only replaces data ping-by-ping. It will never add pings. Any extra
        data in obj_to_insert will be ignored.
        """

        #  determine how many pings we're inserting
        if (index_array):
            n_inserting = index_array.shape[0]
        else:
            idx  = self.get_indices(start_time=ping_time, end_time=ping_time,
                    start_ping=ping_number, end_ping=ping_number)[0]
            n_inserting = self.n_pings - idx
            index_array = np.arange(n_inserting) + idx

        if (obj_to_insert is None):
            #  when obj_to_insert is None, we create automatically create a matching
            #  object that contains no data (all NaNs)
            obj_to_insert = self.empty_like(n_inserting, empty_times=True)

            #  when replacing, we copy the ping times
            obj_to_insert.ping_times = self.ping_times[index_array]

        #  when inserting/replacing data in processed_data objects we have to make sure
        #  the data are the same type. The parent method will check if the frequencies are the same.
        if (self.data_type != obj_to_insert.data_type):
            raise TypeError('You cannot replace data in an object that contains ' +
                    self.data_type.data_type + ' data using an object that ' +
                    'contains ' + obj_to_insert.data_type + ' data.')

        #  get our range/depth vector
        if (hasattr(self, 'range')):
            this_vaxis = getattr(self, 'range')
        else:
            this_vaxis = getattr(self, 'depth')

        #  interppolate the object we're inserting to our vertical axis (if the vertical
        #  axes are the same interpolate will return w/o doing anything.)
        obj_to_insert.interpolate(this_vaxis)

        #  we are now coexisting in harmony - call parent's insert
        super(processed_data, self).replace( obj_to_insert, ping_number=None,
                ping_time=None, insert_after=True, index_array=None)


    def insert(self, obj_to_insert, ping_number=None, ping_time=None,
               insert_after=True, index_array=None):
        """
        insert inserts the data from the provided echolab2.processed_data object into
        this object. The insertion point is specified by ping number or time.

        Args:
            obj_to_insert: an instance of echolab2.processed_data that contains the
                data you are inserting. The object's sample data will be vertically
                interpolated to the vertical axis of this object.

            ping_number: The ping number specifying the insertion point

            ping_time: The ping time specifying the insertion point

            If you specify a ping number or ping time, existing data from
            the insertion point on will be shifted after the inserted data.

            insert_after: Set to True to insert *after* the specified ping time
                or ping number. Set to False to insert *at* the specified time
                or ping number.

            index_array: A numpy array containing the indices of the pings you
                want to insert. Unlike when using a ping number or ping time,
                the pings do not have to be consecutive. When this keyword is
                present, the ping_number, ping_time and insert_after keywords
                are ignored.
        """
        #  determine how many pings we're inserting
        if (index_array is None):
            in_idx  = self.get_indices(start_time=ping_time, end_time=ping_time,
                    start_ping=ping_number, end_ping=ping_number)[0]
            n_inserting = self.n_pings - in_idx
        else:
            n_inserting = index_array.shape[0]

        if (obj_to_insert is None):
            #  when obj_to_insert is None, we create automatically create a
            # matching object that contains no data (all NaNs)
            obj_to_insert = self.empty_like(n_inserting, empty_times=True)

        #  check that the data types are the same
        if (self.data_type != obj_to_insert.data_type):
            raise TypeError('You cannot insert an object that contains ' +
                    obj_to_insert.data_type + ' data into an object that ' +
                    'contains ' + self.data_type + ' data.')

        #  get our range/depth vector
        if (hasattr(self, 'range')):
            this_vaxis = getattr(self, 'range')
        else:
            this_vaxis = getattr(self, 'depth')

        #  interpolate the object we're inserting to our vertical axis (if
        # the vertical axes are the same interpolate will return w/o doing
        # anything.)
        obj_to_insert.interpolate(this_vaxis)

        #  we are now coexisting in harmony - call parent's insert
        super(processed_data, self).insert(obj_to_insert,
                                           ping_number=ping_number,
                                           ping_time=ping_time,
                                           insert_after=insert_after,
                                           index_array=index_array)


    def empty_like(self, n_pings=None, empty_times=False, channel_id=None):
        """
        empty_like returns a processed_data object with the same general
        characteristics of "this" object with all of the data arrays
        filled with NaNs

        Args:
            n_pings: Set n_pings to an integer specifying the number of pings
                in the new object. By default the number of pings will match
                this object's ping count. The vertical axis (both number of
                samples and depth/range values) will be the same as this object.

            empty_times: Set empty_times to True to return an object with
                an "empty" ping_time attribute (all values set to NaT).
                If n_pings is set and it does not equal this object's n_pings
                value this keyword is forced to True since there isn't a
                1:1 mapping of times between the existing and new object.

            channel_id: Set channel_id to a string specifying the channel_id
                for the new object. If this value is None, the channel_id is
                copied from this object's id.

        """

        #  get an empty processed_data object "like" this object
        empty_obj = self._like(n_pings)

        #  call the parent _like helper method and return the result
        return self._like(empty_obj, n_pings, np.nan, empty_times=False,
                channel_id=None)


    def zeros_like(self, n_pings=None, empty_times=False, channel_id=None):
        """
        zeros_like returns a processed_data object with the same general
        characteristics of "this" object with all of the data arrays
        filled with zeros

        This method is commonly used to create synthetic channels.

        Args:
            n_pings: Set n_pings to an integer specifying the number of pings
                in the new object. By default the number of pings will match
                this object's ping count. The vertical axis (both number of
                samples and depth/range values) will be the same as this object.

            empty_times: Set empty_times to True to return an object with
                an "empty" ping_time attribute (all values set to NaT).
                If n_pings is set and it does not equal this object's n_pings
                value this keyword is forced to True since there isn't a
                1:1 mapping of times between the existing and new object.

            channel_id: Set channel_id to a string specifying the channel_id
                for the new object. If this value is None, the channel_id is
                copied from this object's id.
        """

        #  get an empty processed_data object "like" this object
        empty_obj = self._like(n_pings)

        #  call the parent _like helper method and return the result
        return self._like(empty_obj, n_pings, 0.0, empty_times=False,
                channel_id=None)


    def copy(self):
        """
        copy creates a deep copy of this object.
        """

        #  create an empty processed_data object with the same basic props as ourself
        pd_copy = processed_data(self.channel_id,
                self.frequency, self.data_type)

        #  copy the other base attributes of our class
        pd_copy.sample_thickness = self.sample_thickness
        pd_copy.sample_offset = self.sample_offset

        #  call the parent _copy helper method and return the result
        return self._copy(pd_copy)


    def pad_top(self, n_samples):
        """
        pad_top shifts the data array vertically the specified number of samples
        and insert NaNs. The range or depth axis is updated accordingly.

        This method differs from shift_pings in that that you must shift by whole
        samples. No interpolation is performed.
        """
        #  store the old sample number
        old_samples = self.n_samples

        #  resize the sample data arrays
        self.resize(self.n_pings, self.n_samples + n_samples)

        #  generate the new range/depth array
        if (hasattr(self, 'range')):
            attr = getattr(self, 'range')
        else:
            attr = getattr(self, 'depth')
        attr[:] = (np.arange(self.n_samples) - n_samples) * self.sample_thickness + attr[0]

        #  shift the sample data atrributes
        for attr_name in self._data_attributes:
            #  get the attribute
            attr = getattr(self, attr_name)
            #  check if it is a 2d array (which is a sample data array)
            if (attr.ndim == 2):
                #  this is a sample data array - shift the data and pad
                attr[:,n_samples:] = attr[:,0:old_samples]
                attr[:,0:n_samples] = np.nan


    def shift_pings(self, vert_shift, to_depth=False):
        """
        shift_pings shifts sample data vertically by an arbitrary amount,
        interpolating sample data to the new vertical axis.

            vert_shift is a scalar or vector n_pings long that contains the
            constant shift for all pings or a per-ping shift respectively.

            Set to_depth to True if you are converting from range to depth
            This option will remove the range attribute and replace it with
            the depth attribute.

        """

        #  determine the vertical extent of the shift
        min_shift = np.min(vert_shift)
        max_shift = np.max(vert_shift)
        vert_ext = max_shift - min_shift

        #  determine our vertical axis - this has to be range or depth
        if hasattr(self, 'range'):
            vert_axis = self.range
        else:
            vert_axis = self.depth
            #  if we've already converted to depth, unset the to_depth keyword
            to_depth = False

        #  if there is a new vertical extent resize our arrays
        if (vert_ext != 0):
            #  determine the number of new samples as a result of the shift
            new_samps = (np.ceil(vert_ext.astype('float32') / self.sample_thickness)).astype('uint')
            # calculate new sample dimension
            new_sample_dim = (self.n_samples+new_samps).astype('uint')
            #  and resize (n_samples will be updated in the _resize method)
            old_samps = self.n_samples
            self.resize(self.n_pings, new_sample_dim)

        # create the new vertical axis
        new_axis = (np.arange(self.n_samples) * self.sample_thickness) + np.min(vert_axis) + min_shift

        #  check if this is not a constant shift
        if (vert_ext != 0):
            #  not constant, work thru the 2d attributes and interpolate the sample data

            #  first convert to linear units if required
            if (self.data_type[0] == 'S'):
                is_log = True
                self.to_linear()
            else:
                is_log = False
            #  then pick out the sample data arrays and interpolate
            for attr_name in self._data_attributes:
                attr = getattr(self, attr_name)
                if (isinstance(attr, np.ndarray) and (attr.ndim == 2)):
                    for ping in range(self.n_pings):
                        attr[ping,:] = np.interp(new_axis, vert_axis + vert_shift[ping],
                                attr[ping,:old_samps], left=np.nan, right=np.nan)
            #  convert back to log units if required
            if (is_log):
                self.to_log()

        # and assign the new axis
        if (to_depth):
            #  if we're converting from range to depth, add depth and remove range
            self.add_attribute('depth', new_axis)
            self.remove_attribute('range')
        else:
            #  no conversion, just assign the new vertical axis data
            vert_axis = new_axis


    def to_linear(self):
        """
        to_linear converts sample data from log to linear
        """

        if (self.data_type == 'Sv'):
            self.add_attribute('sv', 10.0 ** (self.Sv / 10.0))
            self.data_type = 'sv'
            self.remove_attribute('Sv')
        elif (self.data_type == 'Sp'):
            self.add_attribute('sp', 10.0 ** (self.Sp / 10.0))
            self.data_type = 'sp'
            self.remove_attribute('Sp')


    def to_log(self):
        """
        to_log converts sample data from linear to log
        """

        if (self.data_type == 'sv'):
            self.add_attribute('Sv', 10.0 * np.log10(self.sv))
            self.data_type = 'Sv'
            self.remove_attribute('sv')
        elif (self.data_type == 'sp'):
            self.add_attribute('Sp', 10.0 * np.log10(self.sp))
            self.data_type = 'Sp'
            self.remove_attribute('sp')


    def interpolate(self, new_vaxis):
        """
        interpolate vertically interpolates our sample data to a new vertical
        axis. If the new vertical axis has more samples than the existing
        vertical axis the sample data array will be resized.

        """

        #  get the existing vertical axis
        if (hasattr(self, 'range')):
            old_vaxis = getattr(self, 'range').copy()
        elif (hasattr(self, 'depth')):
            old_vaxis = getattr(self, 'depth').copy()
        else:
            raise AttributeError('The data object has neither'
                                 ' a range nor depth attribute.')

        #  check if we need to vertically resize our sample data
        if (new_vaxis.shape[0] != self.n_samples):
            self.resize(self.n_pings, new_vaxis.shape[0])
        else:
            #  they are the same length - check if they are identical
            if (np.all(np.isclose(old_vaxis, new_vaxis))):
                #  they are the same - nothing to do
                return

        #  update our sample thickness
        self.sample_thickness = np.mean(np.ediff1d(new_vaxis))

        #  convert to linear units if required
        if (self.data_type[0] == 'S'):
            is_log = True
            self.to_linear()
        else:
            is_log = False

        #  pick out the sample data arrays and interpolate
        for attr_name in self._data_attributes:
            attr = getattr(self, attr_name)
            if (isinstance(attr, np.ndarray) and (attr.ndim == 2)):
                for ping in range(self.n_pings):
                    attr[ping,:] = np.interp(new_vaxis, old_vaxis,
                            attr[ping,:old_vaxis.shape[0]], left=np.nan, right=np.nan)

        #  convert back to log units if required
        if (is_log):
            self.to_log()


    def resize(self, new_ping_dim, new_sample_dim):
        """
        resize reimplements sample_data.resize adding updating of the vertical axis and
        n_pings attribute.
        """

        #  get the existing vertical axis
        if (hasattr(self, 'range')):
            vaxis = getattr(self, 'range')
        else:
            vaxis = getattr(self, 'depth')

        #  and generate the new vertical axis
        vaxis = np.arange(new_sample_dim) * self.sample_thickness + vaxis[0]

        #  call the parent method to resize the arrays (n_samples is updated here)
        super(processed_data, self).resize(new_ping_dim, new_sample_dim)

        #  and then update n_pings
        self.n_pings = self.ping_time.shape[0]


    def __setitem__(self, key, value):
        """
        we can assign to sample data elements in processed_data objects using
        assignment with mask objects or we can use python array slicing and
        assign data from one processed_data object to this object (i.e. replace)

        When assigning with a mask, the assigment is to the sample data only.
        Currently echolab2 only supports assigning sample data that share the exact
        shape of the mask or data that can be broadcasted into this shape. Scalars
        always work and if using a sample mask, arrays that are the same size as the
        mask work. You'll need to think about how this applies to ping masks
        if you want to assign using these.

        When assigning with a slice, the assigment is the same as replacement and
        the value passed must be a processed_data object containing the data to
        assign.
        """

        #  determine if we're assigning with a mask or assigning with slice object
        if (isinstance(key, mask.mask)):
            #  it's a mask - make sure the mask applies to this object
            self._check_mask(key)

            if (key.type.lower() == 'sample'):
                #  this is a 2d mask array which we can directly apply to the data
                sample_mask = key.mask
            else:
                #  this is a ping based mask - create a 2d array based on the mask
                #  to apply to the data.
                sample_mask = np.full((self.n_pings,self.n_samples), False, dtype=bool)

                #  set all samples to true for each ping set true in the ping mask
                sample_mask[key.mask,:] = True

            #  set the sample data
            for attr_name in self._data_attributes:
                attr = getattr(self, attr_name)
                if (attr.ndim == 2):
                    attr[sample_mask] = value

        else:
            #  we're dealing with a slice object - generate an index array based
            #  defining the pings to replace
            replace_idx = (np.arange(int(round((key.stop - key.start) /
                    float(key.step)))) * key.step) + key.start

            #  and call the replace method using this index array
            self.replace(value, index_array=replace_idx)


    def __getitem__(self, key):
        """
        processed_data objects can be sliced with standard index based slicing as
        well as mask objects. Mask objects slice differently depending on if they
        are ping or sample masks. Ping masks return a view of the processed_data
        object comprised of pings where the mask is True. Sample masks return a
        numpy array containing the sample data where the mask is True. It DOES
        NOT return a processed data object.
        """

        #  determine if we're "slicing" with a mask or slicing with slice object
        if (isinstance(key, mask.mask)):

            #  make sure the mask applies to this object
            self._check_mask(key)

            if (key.type.lower() == 'sample'):
                #  this is a 2d mask array which we can directly apply to the data
                sample_mask = key.mask
            else:
                #  this is a ping based mask - create a 2d array based on the mask
                #  to apply to the data.
                sample_mask = np.full((self.n_pings,self.n_samples), False, dtype=bool)

                #  set all samples to true for each ping set true in the ping mask
                sample_mask[key.mask,:] = True

            #  return sample data only as a numpy array
            for attr_name in self._data_attributes:
                attr = getattr(self, attr_name)
                if (attr.ndim == 2):
                    p_data = attr[sample_mask]

        else:
            #  we're returning a sliced processed_data object - create a new object to return
            p_data = processed_data(self.channel_id, self.frequency, self.data_type)

            #  copy common attributes
            p_data.sample_thickness = self.sample_thickness
            p_data.sample_dtype = self.sample_dtype
            p_data.frequency = self.frequency
            p_data._data_attributes = list(self._data_attributes)

            #  and work thru the data attributes, slicing them and adding to the new
            #  processed_data object.
            for attr_name in self._data_attributes:
                attr = getattr(self, attr_name)
                if (attr.ndim == 2):
                    #  2d arrays can just be sliced as usual
                    setattr(p_data, attr_name, attr.__getitem__(key))
                else:
                    #  for 1d arrays we need to make sure we pick up the correct slice
                    if (attr.shape[0] == self.n_pings):
                        #  this is a ping axis value - slice and set the new object's attribute
                        sliced_attr = attr.__getitem__(key[0])
                        setattr(p_data, attr_name, sliced_attr)
                        #  update the n_pings attribute
                        p_data.n_pings = sliced_attr.shape[0]
                    else:
                        #  we'll assume this is a sample axis value - slice and set
                        sliced_attr = attr.__getitem__(key[1])
                        setattr(p_data, attr_name, sliced_attr)
                        #  update the n_samples attribute
                        p_data.n_samples = sliced_attr.shape[0]

            #  update the sample_offset if we're slicing on the sample axis
            if (key[1].start):
                p_data.sample_offset += key[1].start

        return p_data


    def _check_mask(self, mask):
        '''
        _check_mask ensures that the mask dimensions and axes values match
        our data's dimensions and values.
        '''
        #  check the ping times and make sure they match
        if (not np.array_equal(self.ping_time, mask.ping_time)):
            raise ValueError('Mask ping times do not match the data ping times.')

        #  make sure the mask's vertical axis (if it exists - ping masks will not have one) is the same
        if (hasattr(mask, 'range')):
            #  mask has range - check if we have range
            if (hasattr(self, 'range')):
                #  we have range - make sure they are the same
                if (not np.array_equal(self.range, mask.range)):
                    raise ValueError("The mask's ranges do not match the data ranges.")
            else:
                #  we don't have range so we must have depth and we can't do that
                raise AttributeError('You cannot compare a range based mask with depth based data.')
        elif (hasattr(mask, 'depth')):
            #  mask has depth - check if we have depth
            if (hasattr(self, 'depth')):
                #  we have depth - make sure they are the same
                if (not np.array_equal(self.depth, mask.depth)):
                    raise ValueError("The mask's depths do not match the data depths.")
            else:
                #  we don't have depth so we must have range and we can't do that
                raise AttributeError('You cannot compare a depth based mask with range based data.')


    def _is_like_me(self, pd_object):
        '''
        _is_like_me ensures that the processed_data object's dimensions and axes
        values match our data's dimensions and values.
        '''

        #  check the ping times and make sure they match
        if (not np.array_equal(self.ping_time, pd_object.ping_time)):
            raise ValueError("The processed_data object's ping times do not match our ping times.")

        #  make sure the vertical axis is the same
        if (hasattr(pd_object, 'range')):
            if (hasattr(self, 'range')):
                if (not np.array_equal(self.range, pd_object.range)):
                    raise ValueError("The processed_data object's ranges do not match our ranges.")
            else:
                raise AttributeError('You cannot compare a range based object with a depth based object.')
        else:
            if (hasattr(self, 'depth')):
                if (not np.array_equal(self.depth, mask.depth)):
                    raise ValueError("The processed_data object's depths do not match our depths.")
            else:
                raise AttributeError('You cannot compare a depth based object with a range based object.')


    def _like(self, n_pings):
        """
        _like is an internal method which creates an empty processed_data object
        that is "like" this object. It is used by the empty_like and zeros_like
        methods.
        """
        #  if we haven'tbeen told how many pings, assume same size as this object
        if (n_pings == None):
            n_pings = self.n_pings

        #  create an instance of echolab2.processed_data and set the same
        #  basic properties as this object.
        empty_obj = processed_data(self.channel_id, self.frequency,
                self.data_type)
        empty_obj.sample_thickness = self.sample_thickness
        empty_obj.sample_offset = self.sample_offset

        return empty_obj


    def __gt__(self, other):
        """
        __gt__ implements the "greater than"  operator. We accept either a like sized
        processed_data object where we will perform an element by element comparison or
        a scalar value.

        The comparison operators always do a element-by-element comparison and return
        the results in a sample mask.
        """

        #  create the mask we will return
        compare_mask = mask.mask(like=self)

        #  determine what we're comparing ourself to
        if (isinstance(other, processed_data.processed_data)):
            #  we've been passed a processed_data object - make sure it's kosher
            self._is_like_me(other)

            compare_mask.mask[:] = self.

        pass


    def __lt__(self, other):
        pass


    def __ge__(self, other):
        pass

    def __le__(self, other):
        pass


    def __eq__(self, other):
        pass

    def __ne__(self, other):
        pass



    def __str__(self):
        '''
        reimplemented string method that provides some basic info about the processed_data object
        '''

        #  print the class and address
        msg = str(self.__class__) + " at " + str(hex(id(self))) + "\n"

        #  print some more info about the processed_data instance
        n_pings = len(self.ping_time)
        if (n_pings > 0):
            msg = msg + "                channel(s): ["
            for channel in self.channel_id:
                msg = msg + channel + ", "
            msg = msg[0:-2] + "]\n"
            msg = msg + "                 frequency: " + str(self.frequency)+ "\n"
            msg = msg + "           data start time: " + str(self.ping_time[0])+ "\n"
            msg = msg + "             data end time: " + str(self.ping_time[n_pings-1])+ "\n"
            msg = msg + "           number of pings: " + str(n_pings)+ "\n"
            msg = msg + "           data attributes:"
            n_attr = 0
            padding = " "
            for attr_name in self._data_attributes:
                attr = getattr(self, attr_name)
                if (n_attr > 0):
                    padding = "                           "
                if (isinstance(attr, np.ndarray)):
                    if (attr.ndim == 1):
                        msg = msg + padding + attr_name + " (%u)\n" % (attr.shape[0])
                    else:
                        msg = msg + padding + attr_name + " (%u,%u)\n" % (attr.shape[0], attr.shape[1])
                elif (isinstance(attr, list)):
                        msg = msg + padding + attr_name + " (%u)\n" % (len(attr))
                n_attr += 1
        else:
            msg = msg + ("  processed_data object contains no data\n")

        return msg
