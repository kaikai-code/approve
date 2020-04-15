def list_of_groups(all_count, per_list_len):
    '''
    :param all_count:   12
    :param per_list_len:  每个小列表的长度
    :return:
    '''
    # list_of_group = zip(*(iter(list_info),) *per_list_len)
    # end_list = [list(i) for i in list_of_group] # i is a tuple
    # count = len(list_info) % per_list_len
    # end_list.append(list_info[-count:]) if count !=0 else end_list

    # num = round(all_count / per_list_len, 2)
    num = all_count / per_list_len
    end_list = []
    start_num = 1
    end_num = num
    while True:
        if start_num > all_count:
            break
        end_list.append([start_num, end_num])
        start_num = end_num + 0.00001
        end_num += num
    return end_list

a = list_of_groups(12, 4)
print(a)
"%Y-%m-%d %H:%M:%S"